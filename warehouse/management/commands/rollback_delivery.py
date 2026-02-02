from collections import defaultdict

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from warehouse.models import (
    Delivery,
    DeliveryItem,
    DeliveryPalette,
    StockSupply,
    StockSupplySettlement,
    StockSupplySell,
    WarehouseStockHistory,
)


class Command(BaseCommand):
    help = (
        "Cofa (usuwa) jedną dostawę Delivery po ID razem z jej elementami.\n"
        "Dodatkowo cofa wpływ na WarehouseStock.quantity (zmniejsza stany) na podstawie WarehouseStockHistory.\n"
        "Jeśli DeliveryItem jest chronione przez StockSupply.delivery_item (PROTECT), usuwa najpierw StockSupply + ich ogon.\n"
        "Domyślnie DRY-RUN."
    )

    def add_arguments(self, parser):
        parser.add_argument("--id", type=int, required=True, help="ID dostawy Delivery do usunięcia.")
        parser.add_argument("--apply", action="store_true", help="Wykonaj usuwanie (domyślnie DRY-RUN).")

    def handle(self, *args, **opts):
        delivery_id = opts["id"]
        apply = opts["apply"]

        try:
            d = Delivery.objects.get(id=delivery_id)
        except Delivery.DoesNotExist:
            raise CommandError(f"Delivery id={delivery_id} does not exist")

        items_qs = DeliveryItem.objects.filter(delivery=d)
        palettes_qs = DeliveryPalette.objects.filter(delivery=d)

        supplies_qs = StockSupply.objects.filter(delivery_item__delivery=d)

        # Ogon powiązany ze StockSupply
        ssh_qs = WarehouseStockHistory.objects.filter(stock_supply__in=supplies_qs)
        sss_qs = StockSupplySettlement.objects.filter(stock_supply__in=supplies_qs)
        sse_qs = StockSupplySell.objects.filter(stock_supply__in=supplies_qs)

        # policz ile cofniemy z magazynów (per WarehouseStock)
        deltas = defaultdict(int)
        for h in ssh_qs.select_related("warehouse_stock"):
            delta = int(h.quantity_after) - int(h.quantity_before)
            if delta:
                deltas[h.warehouse_stock_id] += delta

        self.stdout.write("=== ROLLBACK DELIVERY ===")
        self.stdout.write(f"mode = {'APPLY' if apply else 'DRY-RUN'}")
        self.stdout.write(f"Delivery id={d.id} date={d.date} provider_id={getattr(d, 'provider_id', None)}")
        self.stdout.write("-" * 100)

        self.stdout.write("WAREHOUSESTOCK DECREASE PLAN (from history):")
        if not deltas:
            self.stdout.write("  (no WarehouseStockHistory rows found for these supplies!)")
        else:
            total_back = 0
            for ws_id, qty in sorted(deltas.items()):
                total_back += qty
                self.stdout.write(f"  WarehouseStock id={ws_id} decrease by {qty}")
            self.stdout.write(f"  TOTAL decrease qty = {total_back}")

        self.stdout.write("-" * 100)
        self.stdout.write("TO DELETE (in order):")
        self.stdout.write(f"  WarehouseStockHistory (for these supplies): {ssh_qs.count()}")
        self.stdout.write(f"  StockSupplySettlement (for these supplies): {sss_qs.count()}")
        self.stdout.write(f"  StockSupplySell (for these supplies): {sse_qs.count()}")
        self.stdout.write(f"  StockSupply (from this delivery): {supplies_qs.count()}")
        self.stdout.write(f"  DeliveryItem: {items_qs.count()}")
        self.stdout.write(f"  DeliveryPalette: {palettes_qs.count()}")
        self.stdout.write("  Delivery: 1")
        self.stdout.write("-" * 100)

        if not apply:
            self.stdout.write("DRY-RUN done. Add --apply to execute.")
            return

        with transaction.atomic():
            # 0) Cofnij stany magazynowe (na podstawie historii)
            #    Zależności: history ma FK do WarehouseStock (CASCADE), więc musimy to zrobić PRZED kasowaniem historii.
            if deltas:
                # blokujemy WS, żeby nic równolegle nie ruszało
                ws_map = {
                    ws.id: ws
                    for ws in (
                        WarehouseStockHistory.objects
                        .filter(warehouse_stock_id__in=list(deltas.keys()))
                        .select_related("warehouse_stock")
                        .values_list("warehouse_stock_id", "warehouse_stock")
                    )
                }
                # Powyższe values_list nie zwróci obiektów ws jak chcemy w Django,
                # więc po prostu pobierzmy WarehouseStock normalnie:
                from warehouse.models import WarehouseStock
                locked_ws = (
                    WarehouseStock.objects
                    .select_for_update()
                    .filter(id__in=list(deltas.keys()))
                )
                locked_ws_map = {ws.id: ws for ws in locked_ws}

                for ws_id, qty in deltas.items():
                    ws = locked_ws_map.get(ws_id)
                    if not ws:
                        raise CommandError(f"WarehouseStock id={ws_id} not found while rolling back delivery id={d.id}")

                    if qty > ws.quantity:
                        raise CommandError(
                            f"Cannot rollback: WarehouseStock id={ws_id} has qty={ws.quantity}, "
                            f"but need to decrease by {qty} (would go negative)."
                        )
                    ws.decrease_quantity(qty)

            # 1) usuń ogon StockSupply
            deleted_ssh = ssh_qs.delete()[0]
            deleted_sss = sss_qs.delete()[0]
            deleted_sse = sse_qs.delete()[0]

            # 2) usuń supplies (to odblokuje DeliveryItem)
            deleted_supplies = supplies_qs.delete()[0]

            # 3) usuń elementy dostawy i samą dostawę
            deleted_items = items_qs.delete()[0]
            deleted_palettes = palettes_qs.delete()[0]
            deleted_delivery = d.delete()[0]

        self.stdout.write("DELETED:")
        self.stdout.write(f"  WarehouseStockHistory: {deleted_ssh}")
        self.stdout.write(f"  StockSupplySettlement: {deleted_sss}")
        self.stdout.write(f"  StockSupplySell: {deleted_sse}")
        self.stdout.write(f"  StockSupply: {deleted_supplies}")
        self.stdout.write(f"  DeliveryItem: {deleted_items}")
        self.stdout.write(f"  DeliveryPalette: {deleted_palettes}")
        self.stdout.write(f"  Delivery: {deleted_delivery}")
        self.stdout.write("DONE.")
