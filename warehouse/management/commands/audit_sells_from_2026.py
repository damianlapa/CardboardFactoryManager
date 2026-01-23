from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.core.exceptions import FieldError

import datetime

from warehouse.models import (
    ProductSell3,
    StockSupplySell,
    StockSupplySettlement,
    WarehouseStock,
)


def model_fields_dump(model_cls):
    names = []
    for f in model_cls._meta.get_fields():
        # pomijamy reverse relacje M2M bez nazwy
        names.append(f"{f.name} ({f.__class__.__name__})")
    return ", ".join(names)


class Command(BaseCommand):
    help = "Audit ProductSell3 from 2026-01-01 (safe introspection + settlement path discovery)"

    def handle(self, *args, **options):
        cutoff = datetime.datetime(
            2026, 1, 1, 0, 0, 0,
            tzinfo=timezone.get_current_timezone()
        )

        self.stdout.write("")
        self.stdout.write("=== MODEL FIELDS (INTROSPECTION) ===")
        self.stdout.write(f"ProductSell3 fields: {model_fields_dump(ProductSell3)}")
        self.stdout.write(f"StockSupplySell fields: {model_fields_dump(StockSupplySell)}")
        self.stdout.write(f"StockSupplySettlement fields: {model_fields_dump(StockSupplySettlement)}")

        # Spróbujmy też znaleźć model Settlement, jeśli istnieje w warehouse.models
        SettlementModel = None
        for candidate_name in ["OrderSettlement", "Settlement", "StockSettlement"]:
            try:
                SettlementModel = getattr(__import__("warehouse.models", fromlist=[candidate_name]), candidate_name)
                self.stdout.write(f"{candidate_name} fields: {model_fields_dump(SettlementModel)}")
                break
            except Exception:
                continue

        self.stdout.write("")
        self.stdout.write("=== PRODUCTSELL3 FROM 2026-01-01 ===")

        sells = (
            ProductSell3.objects
            .filter(date__gte=cutoff)   # jeśli pole nazywa się inaczej -> zmień TYLKO 'date'
            .order_by("-date", "-id")
        )

        self.stdout.write(f"Total sells: {sells.count()}")
        self.stdout.write("")

        # Kandydackie ścieżki łączenia StockSupplySettlement -> (settlement -> sell)
        # będziemy próbować po kolei, a błędy ignorować i raportować.
        settlement_paths = [
            "settlement__sell",
            "settlement__productsell",
            "settlement__productsell3",
            "settlement__product_sell",
            "settlement__sale",
            "settlement__sell3",
        ]

        for sell in sells:
            self.stdout.write("=" * 80)
            self.stdout.write(f"SELL id={sell.id} | date={getattr(sell, 'date', None)} | qty={getattr(sell, 'quantity', None)}")
            self.stdout.write(f"  warehouse_stock_id: {getattr(sell, 'warehouse_stock_id', None)}")

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
                    self.stdout.write(f"    supply_id={row['stock_supply_id']} | qty={row['qty']}")
                    fifo_total += int(row["qty"])
            else:
                self.stdout.write("    (BRAK)")
            self.stdout.write(f"    FIFO total qty: {fifo_total}")

            # --- StockSupplySettlement (szukamy przez settlement__X = sell) ---
            self.stdout.write("  StockSupplySettlement (via settlement -> sell candidates):")
            found_any = False
            for path in settlement_paths:
                try:
                    qs = (
                        StockSupplySettlement.objects
                        .filter(**{path: sell})
                        .values("settlement_id", "stock_supply_id", "as_result")
                        .annotate(qty=Coalesce(Sum("quantity"), 0))
                    )
                    if qs.exists():
                        found_any = True
                        self.stdout.write(f"    MATCH PATH: {path}  (rows={qs.count()})")
                        for row in qs[:50]:
                            self.stdout.write(
                                f"      settlement_id={row['settlement_id']} | supply_id={row['stock_supply_id']} | "
                                f"as_result={row['as_result']} | qty={row['qty']}"
                            )
                        # nie szukamy dalej jeśli znaleźliśmy poprawną ścieżkę
                        break
                except FieldError:
                    # ścieżka nie istnieje w ORM
                    continue

            if not found_any:
                self.stdout.write("    (BRAK / nie znaleziono ścieżki)")

            # --- WarehouseStock sanity ---
            try:
                ws = WarehouseStock.objects.get(id=sell.warehouse_stock_id)
                self.stdout.write(f"  WarehouseStock qty NOW: {ws.quantity}")
            except Exception:
                self.stdout.write("  WarehouseStock: DOES NOT EXIST / ERROR")

        self.stdout.write("")
        self.stdout.write("=== END OF REPORT ===")
