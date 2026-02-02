import datetime
from django.core.management.base import BaseCommand
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q

from warehouse.models import (
    ProductSell3,
    StockSupplySell,
    ProductSellOrderPart,
    WarehouseStockHistory,
    StockSupplySettlement,
    OrderSettlementProduct,
    OrderSettlement,
    StockSupply,
    Delivery,
    DeliveryItem,
    DeliveryPalette,
    DeliverySpecial,
    DeliverySpecialItem,
    ProductComplexAssembly,
    ProductComplexParts,
    OrderToOrderShift,
    Order,
    PriceList,
    WarehouseStock,
    StockSupply,
)


class Command(BaseCommand):
    help = (
        "Purge (delete) all records in warehouse app that are dated >= cutoff. "
        "Default DRY-RUN; use --apply to execute. "
        "Optionally rebuild WarehouseStock quantities after purge."
    )

    def add_arguments(self, parser):
        parser.add_argument("--cutoff", required=True, help="Cutoff date YYYY-MM-DD. Purge date >= cutoff.")
        parser.add_argument("--apply", action="store_true", help="Apply changes (default dry-run).")
        parser.add_argument("--no-rebuild", action="store_true", help="Do NOT rebuild WarehouseStock quantities/flags.")
        parser.add_argument("--skip-orders", action="store_true", help="Do NOT delete Order rows even if dated >= cutoff.")

    def handle(self, *args, **opts):
        cutoff = self._parse_date(opts["cutoff"])
        apply = bool(opts["apply"])
        no_rebuild = bool(opts["no_rebuild"])
        skip_orders = bool(opts["skip_orders"])

        self.stdout.write("=== PURGE SINCE ===")
        self.stdout.write(f"cutoff = {cutoff} (purge date >= cutoff)")
        self.stdout.write(f"mode   = {'APPLY' if apply else 'DRY-RUN'}")
        self.stdout.write(f"rebuild= {'NO' if no_rebuild else 'YES'}")
        self.stdout.write(f"orders = {'SKIP' if skip_orders else 'DELETE if dated'}")

        # --- Querysets to purge ---
        sells_qs = ProductSell3.objects.filter(date__gte=cutoff)

        # History rows block deletions via PROTECT, so delete relevant history first:
        hist_qs = WarehouseStockHistory.objects.filter(
            Q(date__gte=cutoff)
            | Q(sell__date__gte=cutoff)
            | Q(stock_supply__date__gte=cutoff)
            | Q(order_settlement__settlement_date__gte=cutoff)
            | Q(assembly__date__gte=cutoff)
        )

        # StockSupply-related children:
        sssell_qs = StockSupplySell.objects.filter(
            Q(sell__date__gte=cutoff) | Q(stock_supply__date__gte=cutoff)
        )
        sell_parts_qs = ProductSellOrderPart.objects.filter(sell__date__gte=cutoff)

        sssett_qs = StockSupplySettlement.objects.filter(
            Q(settlement__settlement_date__gte=cutoff) | Q(stock_supply__date__gte=cutoff)
        )
        osp_qs = OrderSettlementProduct.objects.filter(settlement__settlement_date__gte=cutoff)
        settlements_qs = OrderSettlement.objects.filter(settlement_date__gte=cutoff)

        supplies_qs = StockSupply.objects.filter(date__gte=cutoff)

        # Deliveries:
        deliv_qs = Delivery.objects.filter(date__gte=cutoff)
        deliv_items_qs = DeliveryItem.objects.filter(delivery__date__gte=cutoff)
        deliv_pal_qs = DeliveryPalette.objects.filter(delivery__date__gte=cutoff)

        deliv_spec_qs = DeliverySpecial.objects.filter(date__gte=cutoff)
        deliv_spec_items_qs = DeliverySpecialItem.objects.filter(delivery__date__gte=cutoff)

        # Assemblies:
        assembly_qs = ProductComplexAssembly.objects.filter(date__gte=cutoff)
        assembly_parts_qs = ProductComplexParts.objects.filter(assembly__date__gte=cutoff)

        # Shifts:
        shift_qs = OrderToOrderShift.objects.filter(date__gte=cutoff)

        # Price lists (dated ranges):
        pricelist_qs = PriceList.objects.filter(Q(date_start__gte=cutoff) | Q(date_end__gte=cutoff))

        # Orders (multiple date fields):
        orders_qs = Order.objects.filter(
            Q(customer_date__gte=cutoff)
            | Q(order_date__gte=cutoff)
            | Q(delivery_date__gte=cutoff)
            | Q(production_date__gte=cutoff)
        )

        # --- Report counts ---
        report = [
            ("ProductSellOrderPart", sell_parts_qs.count()),
            ("StockSupplySell", sssell_qs.count()),
            ("WarehouseStockHistory", hist_qs.count()),
            ("StockSupplySettlement", sssett_qs.count()),
            ("OrderSettlementProduct", osp_qs.count()),
            ("OrderSettlement", settlements_qs.count()),
            ("ProductSell3", sells_qs.count()),
            ("ProductComplexParts", assembly_parts_qs.count()),
            ("ProductComplexAssembly", assembly_qs.count()),
            ("DeliveryPalette", deliv_pal_qs.count()),
            ("DeliveryItem", deliv_items_qs.count()),
            ("Delivery", deliv_qs.count()),
            ("DeliverySpecialItem", deliv_spec_items_qs.count()),
            ("DeliverySpecial", deliv_spec_qs.count()),
            ("StockSupply", supplies_qs.count()),
            ("OrderToOrderShift", shift_qs.count()),
            ("PriceList", pricelist_qs.count()),
        ]
        if not skip_orders:
            report.append(("Order", orders_qs.count()))

        self.stdout.write("\n--- COUNTS TO PURGE ---")
        total = 0
        for name, cnt in report:
            self.stdout.write(f"{name:24s}: {cnt}")
            total += cnt
        self.stdout.write(f"{'TOTAL (rows)':24s}: {total}")

        if not apply:
            self.stdout.write("\nDRY-RUN only. Re-run with --apply to execute deletes.")
            return

        # --- APPLY in a single transaction ---
        with transaction.atomic():
            self.stdout.write("\n--- APPLY DELETE (in dependency-safe order) ---")

            # 1) Small dependents first
            self._del("ProductSellOrderPart", sell_parts_qs)
            self._del("StockSupplySell", sssell_qs)

            # 2) History (PROTECT blocker)
            self._del("WarehouseStockHistory", hist_qs)

            # 3) Settlement graph
            self._del("StockSupplySettlement", sssett_qs)
            self._del("OrderSettlementProduct", osp_qs)
            self._del("OrderSettlement", settlements_qs)

            # 4) Sales
            self._del("ProductSell3", sells_qs)

            # 5) Assemblies
            self._del("ProductComplexParts", assembly_parts_qs)
            self._del("ProductComplexAssembly", assembly_qs)

            # 6) Deliveries palettes (zależne od delivery) - mogą iść wcześniej
            self._del("DeliveryPalette", deliv_pal_qs)

            # 7) StockSupply rows (MUSI być przed DeliveryItem, bo delivery_item jest PROTECT)
            self._del("StockSupply", supplies_qs)

            # 8) Deliveries items + deliveries
            self._del("DeliveryItem", deliv_items_qs)
            self._del("Delivery", deliv_qs)

            # 9) Orders (optional)
            if not skip_orders:
                self._del("Order", orders_qs)

            # 10) Rebuild quantities to match remaining supplies (recommended)
            if not no_rebuild:
                self.stdout.write("\n--- REBUILD WarehouseStock quantities from remaining supplies ---")
                self._rebuild_ws_quantities()

        self.stdout.write(self.style.SUCCESS("DONE. Purge applied successfully."))

    def _parse_date(self, s: str) -> datetime.date:
        try:
            y, m, d = map(int, s.split("-"))
            return datetime.date(y, m, d)
        except Exception:
            raise ValidationError("Invalid --cutoff format. Use YYYY-MM-DD")

    def _del(self, label: str, qs):
        cnt = qs.count()
        if cnt == 0:
            self.stdout.write(f"{label:24s}: 0 (skip)")
            return
        deleted = qs.delete()
        # deleted is (num_deleted, { 'app.Model': num, ...})
        self.stdout.write(f"{label:24s}: deleted {deleted[0]}")

    def _rebuild_ws_quantities(self):
        """
        Sets WarehouseStock.quantity to sum of remaining available quantities from supplies
        matched by (name, stock_type). Also refreshes used flags on supplies.
        """
        # Refresh used flags (safe, but can be a lot)
        supplies = StockSupply.objects.all().only("id")
        # Best effort: call refresh_used_flag if exists
        refreshed = 0
        for s in supplies.iterator(chunk_size=500):
            try:
                s.refresh_used_flag(save=True)
                refreshed += 1
            except Exception:
                pass
        self.stdout.write(f"StockSupply.refresh_used_flag: attempted {refreshed}")

        # Rebuild WS from available quantities
        ws_qs = WarehouseStock.objects.select_related("stock", "warehouse")
        updated = 0
        for ws in ws_qs.iterator(chunk_size=200):
            try:
                name = ws.stock.name
                st = ws.stock.stock_type
                total = 0
                for ss in StockSupply.objects.filter(name=name, stock_type=st).only("id", "quantity", "used").iterator(chunk_size=500):
                    try:
                        total += int(ss.available_quantity())
                    except Exception:
                        # if available_quantity missing/broken, fallback to raw quantity
                        total += int(ss.quantity or 0)
                if int(ws.quantity) != int(total):
                    ws.quantity = int(total)
                    ws.save(update_fields=["quantity"])
                    updated += 1
            except Exception:
                continue
        self.stdout.write(f"WarehouseStock.quantity updated: {updated}")
