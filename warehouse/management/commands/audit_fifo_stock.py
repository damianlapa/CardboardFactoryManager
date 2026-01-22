from django.core.management.base import BaseCommand
from django.db.models import Sum
from django.db.models.functions import Coalesce

from warehouse.models import (
    WarehouseStock,
    StockSupply,
    StockSupplySell,
    StockSupplySettlement,
)


class Command(BaseCommand):
    help = "Audit FIFO consistency: WarehouseStock.quantity vs available StockSupply quantities"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Limit number of WarehouseStock rows to check (0 = no limit)",
        )
        parser.add_argument(
            "--details",
            action="store_true",
            help="Show detailed StockSupply breakdown for mismatches",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        show_details = options["details"]

        qs = WarehouseStock.objects.select_related("warehouse", "stock").order_by("id")
        if limit > 0:
            qs = qs[:limit]

        mismatches = 0

        for ws in qs:
            # Partie, które faktycznie budowały ten stan (IN history z stock_supply)
            supplies = (
                StockSupply.objects
                .filter(
                    warehousestockhistory__warehouse_stock=ws,
                    warehousestockhistory__stock_supply__isnull=False,
                )
                .distinct()
            )

            total_available = 0
            supply_rows = []

            for s in supplies:
                sold = (
                    StockSupplySell.objects
                    .filter(stock_supply=s)
                    .aggregate(t=Coalesce(Sum("quantity"), 0))["t"]
                )
                settled_out = (
                    StockSupplySettlement.objects
                    .filter(stock_supply=s, as_result=False)
                    .aggregate(t=Coalesce(Sum("quantity"), 0))["t"]
                )

                available = int(s.quantity) - int(sold) - int(settled_out)
                total_available += max(available, 0)

                supply_rows.append(
                    (
                        s.id,
                        s.date,
                        s.quantity,
                        sold,
                        settled_out,
                        available,
                    )
                )

            if total_available != ws.quantity:
                mismatches += 1
                self.stdout.write(self.style.ERROR(
                    f"[MISMATCH] WS id={ws.id} | "
                    f"{ws.warehouse.name} | {ws.stock.name}"
                ))
                self.stdout.write(
                    f"  WS.quantity = {ws.quantity} | FIFO available = {total_available}"
                )

                if show_details:
                    for row in supply_rows:
                        sid, date, qty, sold, out, av = row
                        self.stdout.write(
                            f"    Supply {sid} | date={date} | "
                            f"qty={qty} | sold={sold} | out={out} | available={av}"
                        )

        if mismatches == 0:
            self.stdout.write(self.style.SUCCESS("✔ FIFO audit OK — no mismatches found"))
        else:
            self.stdout.write(self.style.WARNING(
                f"⚠ FIFO audit finished — mismatches found: {mismatches}"
            ))
