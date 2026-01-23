from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Sum
from django.db.models.functions import Coalesce

import datetime

from warehouse.models import (
    ProductSell3,
    StockSupplySell,
    StockSupplySettlement,
    WarehouseStock,
)


class Command(BaseCommand):
    help = "Audit ProductSell3 from 2026-01-01 with full rollback-relevant data"

    def handle(self, *args, **options):
        cutoff = datetime.datetime(
            2026, 1, 1, 0, 0, 0,
            tzinfo=timezone.get_current_timezone()
        )

        sells = (
            ProductSell3.objects
            .filter(date__gte=cutoff)   # ⚠️ jeśli pole nazywa się inaczej, zmień TYLKO 'date'
            .order_by("-date", "-id")
        )

        self.stdout.write("")
        self.stdout.write("=== PRODUCTSELL3 FROM 2026-01-01 ===")
        self.stdout.write(f"Total sells: {sells.count()}")
        self.stdout.write("")

        for sell in sells:
            self.stdout.write("=" * 80)
            self.stdout.write(
                f"SELL id={sell.id} | date={sell.date} | qty={sell.quantity}"
            )

            self.stdout.write(
                f"  warehouse_stock_id: {sell.warehouse_stock_id}"
            )

            # --- FIFO (StockSupplySell) ---
            fifo_rows = (
                StockSupplySell.objects
                .filter(sell=sell)
                .values("stock_supply_id")
                .annotate(qty=Coalesce(Sum("quantity"), 0))
            )

            fifo_total = 0
            self.stdout.write("  StockSupplySell:")
            if fifo_rows:
                for row in fifo_rows:
                    self.stdout.write(
                        f"    supply_id={row['stock_supply_id']} | qty={row['qty']}"
                    )
                    fifo_total += int(row["qty"])
            else:
                self.stdout.write("    (BRAK)")

            self.stdout.write(f"    FIFO total qty: {fifo_total}")

            # --- Settlementy powiązane ze sprzedażą ---
            settlement_rows = (
                StockSupplySettlement.objects
                .filter(sell=sell)
                .values("stock_supply_id", "as_result")
                .annotate(qty=Coalesce(Sum("quantity"), 0))
            )

            settlement_total = 0
            self.stdout.write("  StockSupplySettlement:")
            if settlement_rows:
                for row in settlement_rows:
                    self.stdout.write(
                        f"    supply_id={row['stock_supply_id']} | "
                        f"as_result={row['as_result']} | qty={row['qty']}"
                    )
                    settlement_total += int(row["qty"])
            else:
                self.stdout.write("    (BRAK)")

            self.stdout.write(
                f"    Settlement total qty: {settlement_total}"
            )

            # --- WarehouseStock sanity ---
            try:
                ws = WarehouseStock.objects.get(id=sell.warehouse_stock_id)
                self.stdout.write(
                    f"  WarehouseStock qty NOW: {ws.quantity}"
                )
            except WarehouseStock.DoesNotExist:
                self.stdout.write(
                    "  WarehouseStock: DOES NOT EXIST"
                )

        self.stdout.write("")
        self.stdout.write("=== END OF REPORT ===")
