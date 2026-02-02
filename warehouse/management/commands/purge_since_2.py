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

    def _confirm_or_abort(self, prompt: str):
        """
        Interaktywne potwierdzenie w konsoli.
        Wymaga wpisania 'TAK' albo 'YES' (case-insensitive).
        """
        try:
            ans = input(f"\n{prompt}\nWpisz TAK/YES aby kontynuować: ").strip().lower()
        except EOFError:
            ans = ""
        if ans not in ("tak", "yes"):
            raise ValidationError("REBUILD przerwany: brak potwierdzenia użytkownika.")

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
        Rebuild tylko dla istniejących WarehouseStock z qty>0.
        Niczego nie tworzy.
        Pomija:
          - warehouse == "MAGAZYN MATERIAŁÓW POMOCNICZYCH"
          - stock_type == "special"
        Ustawia ws.quantity = suma dostępnych ilości z partii StockSupply (available_quantity)
        dopasowanych po (name, stock_type).
        """
        # 1) Bierzemy TYLKO aktualnie istniejące pozycje z qty>0,
        #    i dodatkowo wykluczamy pomocniczy + special
        ws_qs = (
            WarehouseStock.objects
            .select_related("stock", "stock__stock_type", "warehouse")
            .filter(quantity__gt=0)
            .exclude(warehouse__name="MAGAZYN MATERIAŁÓW POMOCNICZYCH")
            .exclude(stock__stock_type__stock_type="special")
        )

        # 2) Pre-scan: policz ile będzie zmian (bez zapisu)
        to_change = []  # (ws_id, old, new, stock_name, wh_name)
        checked = 0

        for ws in ws_qs.iterator(chunk_size=200):
            checked += 1
            name = ws.stock.name
            st = ws.stock.stock_type

            supplies = (
                StockSupply.objects
                .filter(name=name, stock_type=st)
                .only("id", "quantity", "used", "value")  # value nie trzeba, ale często się przydaje do debug
            )

            total = 0
            for ss in supplies.iterator(chunk_size=500):
                try:
                    total += int(ss.available_quantity())
                except Exception:
                    total += int(ss.quantity or 0)

            if int(ws.quantity) != int(total):
                to_change.append((ws.id, int(ws.quantity), int(total), name, ws.warehouse.name))

        # 3) Raport + potwierdzenie
        self.stdout.write("\n--- REBUILD PLAN (qty>0 only) ---")
        self.stdout.write(f"WarehouseStock checked: {checked}")
        self.stdout.write(f"WarehouseStock to update: {len(to_change)}")
        if to_change:
            self.stdout.write("First 30 diffs:")
            for row in to_change[:30]:
                ws_id, old, new, name, wh = row
                self.stdout.write(f"  WS#{ws_id} | {wh} | {name} | {old} -> {new}")

        # ZAWSZE pytamy przed rebuildem (tak jak chcesz)
        self._confirm_or_abort(
            f"REBUILD ustawi ws.quantity wg StockSupply.available_quantity "
            f"(tylko qty>0, bez tworzenia, z wykluczeniami). "
            f"Zmian: {len(to_change)}. Kontynuować?"
        )

        # 4) Apply: zapisujemy zmiany + odświeżamy used flag TYLKO dla dotkniętych pozycji
        updated = 0
        refreshed = 0

        # zbieramy unikalne (name, stock_type_id) dla odświeżenia used flag oszczędnie
        touched_keys = set()

        for ws_id, old, new, name, wh in to_change:
            try:
                ws = WarehouseStock.objects.select_for_update().get(pk=ws_id)
                ws.quantity = int(new)
                ws.save(update_fields=["quantity"])
                updated += 1

                touched_keys.add((name, ws.stock.stock_type_id))
            except Exception:
                continue

        # refresh used flag tylko dla partii powiązanych z dotkniętymi stockami
        for (name, st_id) in touched_keys:
            qs = StockSupply.objects.filter(name=name, stock_type_id=st_id).only("id", "used", "quantity", "value")
            for ss in qs.iterator(chunk_size=500):
                try:
                    ss.refresh_used_flag(save=True)
                    refreshed += 1
                except Exception:
                    pass

        self.stdout.write(f"WarehouseStock.quantity updated: {updated}")
        self.stdout.write(f"StockSupply.refresh_used_flag (touched only): attempted {refreshed}")

