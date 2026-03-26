import datetime
from django.core.management.base import BaseCommand
from django.db import transaction

from warehouse.models import (
    # Transakcje / historia / stany / partie:
    WarehouseStockHistory,
    WarehouseStock,
    StockSupply,
    StockSupplySettlement,
    StockSupplySell,
    OrderSettlement,
    OrderSettlementProduct,
    ProductSell3,
    ProductSellOrderPart,
    OrderToOrderShift,
    ProductComplexAssembly,
    ProductComplexParts,
    MonthResults,  # jeśli chcesz też czyścić - zostawiamy w wipe (możesz wyłączyć flagą)

    # Dostawy:
    Delivery,
    DeliveryItem,
    DeliveryPalette,
    DeliverySpecial,
    DeliverySpecialItem,
)


CUTOFF = datetime.date(2025, 12, 31)  # zostają <= 2025-12-31, kasujemy >


class Command(BaseCommand):
    help = (
        "Czyści transakcyjne dane magazynowe (historia/stany/partie/settlements/sprzedaże/rozliczenia),\n"
        "a dostawy usuwa tylko dla dat > 2025-12-31 (Delivery/DeliveryItem/DeliverySpecial/...)\n"
        "Domyślnie DRY-RUN."
    )

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Wykonaj usuwanie (domyślnie DRY-RUN).")
        parser.add_argument(
            "--wipe-month-results",
            action="store_true",
            help="Usuń też MonthResults (jeśli chcesz całkowicie czysto w raportach).",
        )

    def handle(self, *args, **opts):
        apply = opts["apply"]
        wipe_month_results = opts["wipe_month_results"]

        self.stdout.write("=== WIPE STOCK TRANSACTIONS (KEEP DELIVERIES <= 2025-12-31) ===")
        self.stdout.write(f"mode = {'APPLY' if apply else 'DRY-RUN'}")
        self.stdout.write(f"cutoff = {CUTOFF} (delete deliveries where date > cutoff)")
        self.stdout.write(f"wipe_month_results = {wipe_month_results}")
        self.stdout.write("-" * 100)

        # 1) Policz ile dostaw poleci (tylko > cutoff)
        deliveries_qs = Delivery.objects.filter(date__gt=CUTOFF)
        delivery_items_qs = DeliveryItem.objects.filter(delivery__date__gt=CUTOFF)
        delivery_palettes_qs = DeliveryPalette.objects.filter(delivery__date__gt=CUTOFF)

        deliveries_special_qs = DeliverySpecial.objects.filter(date__gt=CUTOFF)
        deliveries_special_items_qs = DeliverySpecialItem.objects.filter(delivery__date__gt=CUTOFF)

        self.stdout.write("DELIVERIES TO DELETE (> cutoff):")
        self.stdout.write(f"  Delivery: {deliveries_qs.count()}")
        self.stdout.write(f"  DeliveryItem: {delivery_items_qs.count()}")
        self.stdout.write(f"  DeliveryPalette: {delivery_palettes_qs.count()}")
        self.stdout.write(f"  DeliverySpecial: {deliveries_special_qs.count()}")
        self.stdout.write(f"  DeliverySpecialItem: {deliveries_special_items_qs.count()}")
        self.stdout.write("-" * 100)

        # 2) Policz “transakcje” do pełnego wyczyszczenia
        wipe_models = [
            WarehouseStockHistory,
            StockSupplySettlement,
            StockSupplySell,
            OrderSettlementProduct,
            ProductSellOrderPart,
            ProductComplexParts,
            ProductComplexAssembly,
            OrderToOrderShift,
            ProductSell3,
            OrderSettlement,
            StockSupply,
            WarehouseStock,
        ]
        if wipe_month_results:
            wipe_models = [MonthResults] + wipe_models

        self.stdout.write("TRANSACTION TABLES TO WIPE (ALL ROWS):")
        total = 0
        for m in wipe_models:
            c = m.objects.count()
            total += c
            self.stdout.write(f"  {m._meta.label}: {c}")
        self.stdout.write("-" * 100)
        self.stdout.write(f"TOTAL rows to delete (transactions only): {total}")
        self.stdout.write("-" * 100)

        if not apply:
            self.stdout.write("DRY-RUN done. Add --apply to execute.")
            return

        with transaction.atomic():
            # A) Najpierw kasujemy dostawy tylko > cutoff (dzieci -> rodzice)
            #    (bo Delivery ma PROTECT w DeliveryItem/DeliveryPalette)
            di = delivery_items_qs.delete()[0]
            dp = delivery_palettes_qs.delete()[0]
            ds_items = deliveries_special_items_qs.delete()[0]

            d = deliveries_qs.delete()[0]
            ds = deliveries_special_qs.delete()[0]

            self.stdout.write(f"Deleted DeliveryItem: {di}")
            self.stdout.write(f"Deleted DeliveryPalette: {dp}")
            self.stdout.write(f"Deleted DeliverySpecialItem: {ds_items}")
            self.stdout.write(f"Deleted Delivery: {d}")
            self.stdout.write(f"Deleted DeliverySpecial: {ds}")

            # B) Potem wycieramy całą warstwę transakcji (kolejność od FK do korzeni)
            for m in wipe_models:
                c = m.objects.count()
                if c:
                    self.stdout.write(f"Wiping {m._meta.label} ... ({c})")
                    m.objects.all().delete()

        self.stdout.write("APPLY done.")
