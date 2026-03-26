import datetime
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q

from warehouse.models import (
    WarehouseStock,
    StockSupply,
    StockSupplySell,
    StockSupplySettlement,
    ProductSell3,
    WarehouseStockHistory,
)


class Command(BaseCommand):
    help = (
        "Cleanup StockSupply value=0 duplicates (rewire refs to valued supplies), "
        "then reconcile StockSupply availability to match WarehouseStock.quantity "
        "AS OF a fixed date (default: 2025-12-31). "
        "Default DRY-RUN; use --apply."
    )

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Apply changes (default dry-run).")

        parser.add_argument("--date", default="2025-12-31", help="Audit date YYYY-MM-DD (default: 2025-12-31).")

        # Phase toggles
        parser.add_argument("--skip-cleanup", action="store_true", help="Skip zero-value StockSupply cleanup phase.")
        parser.add_argument("--skip-reconcile", action="store_true", help="Skip reconcile phase.")

        # Scope filters
        parser.add_argument("--only-warehouse-id", type=int, default=None)
        parser.add_argument("--only-stock-id", type=int, default=None)
        parser.add_argument("--min-ws-qty", type=int, default=1)
        parser.add_argument("--limit", type=int, default=0)

        # Cleanup controls
        parser.add_argument(
            "--cleanup-key",
            default="delivery",
            choices=["delivery", "loose"],
            help=(
                "How to match duplicates: "
                "'delivery' = (delivery_item, stock_type, name, date, quantity, dimensions); "
                "'loose' = (stock_type, name, date, quantity, dimensions)."
            ),
        )

    def handle(self, *args, **opts):
        apply = bool(opts["apply"])
        limit = int(opts["limit"]) or None
        min_ws_qty = int(opts["min_ws_qty"])
        skip_cleanup = bool(opts["skip_cleanup"])
        skip_reconcile = bool(opts["skip_reconcile"])
        cleanup_key = opts["cleanup_key"]

        y, m, d = map(int, opts["date"].split("-"))
        adj_date = datetime.date(y, m, d)

        self.stdout.write("=== RECONCILE @ 2025-12-31 (CLEANUP + ALIGN) ===")
        self.stdout.write(f"mode = {'APPLY' if apply else 'DRY-RUN'}")
        self.stdout.write(f"date = {adj_date}")
        self.stdout.write(f"skip_cleanup={skip_cleanup} skip_reconcile={skip_reconcile}")
        self.stdout.write(f"cleanup_key={cleanup_key}")
        self.stdout.write("")

        if not skip_cleanup:
            self._phase_cleanup(apply=apply, cleanup_key=cleanup_key)

        if not skip_reconcile:
            self._phase_reconcile(
                apply=apply,
                adj_date=adj_date,
                min_ws_qty=min_ws_qty,
                only_warehouse_id=opts["only_warehouse_id"],
                only_stock_id=opts["only_stock_id"],
                limit=limit,
            )

        self.stdout.write("\nDONE.")

    # ============================================================
    # PHASE A: cleanup
    # ============================================================
    def _phase_cleanup(self, *, apply: bool, cleanup_key: str):
        self.stdout.write("=== PHASE A: CLEANUP zero-value StockSupply duplicates (rewire refs) ===")

        # kandydaci: value=0 lub NULL
        zero_qs = StockSupply.objects.filter(Q(value=Decimal("0.00")) | Q(value__isnull=True)).order_by("id")

        # indeks valued supplies dla szybkiego matchowania
        valued_qs = StockSupply.objects.exclude(Q(value=Decimal("0.00")) | Q(value__isnull=True)).order_by("id")

        def key_for(s: StockSupply):
            if cleanup_key == "delivery":
                return (
                    s.delivery_item_id,
                    s.stock_type_id,
                    s.name,
                    s.date,
                    int(s.quantity or 0),
                    (s.dimensions or None),
                )
            # loose
            return (
                s.stock_type_id,
                s.name,
                s.date,
                int(s.quantity or 0),
                (s.dimensions or None),
            )

        valued_map = {}
        for s in valued_qs.iterator():
            k = key_for(s)
            # jeśli jest kilka, bierzemy najstarszy (pierwszy) jako KEEP
            valued_map.setdefault(k, s.id)

        pairs = []
        for z in zero_qs.iterator():
            k = key_for(z)
            keep_id = valued_map.get(k)
            if keep_id:
                pairs.append((keep_id, z.id))

        self.stdout.write(f"pairs found (KEEP value>0 <- DELETE value=0): {len(pairs)}")

        rewired = 0
        deleted = 0

        for keep_id, del_id in pairs[:1000000]:
            # na sucho: tylko raport
            if not apply:
                self.stdout.write(f"DRY-RUN: would rewire refs {del_id} -> {keep_id} and delete {del_id}")
                continue

            with transaction.atomic():
                keep = StockSupply.objects.select_for_update().get(pk=keep_id)
                victim = StockSupply.objects.select_for_update().get(pk=del_id)

                # przepnij FK
                StockSupplySell.objects.filter(stock_supply_id=victim.id).update(stock_supply_id=keep.id)
                StockSupplySettlement.objects.filter(stock_supply_id=victim.id).update(stock_supply_id=keep.id)
                WarehouseStockHistory.objects.filter(stock_supply_id=victim.id).update(stock_supply_id=keep.id)

                rewired += 1

                # dopiero teraz kasuj (po przepięciu)
                victim.delete()
                deleted += 1

        self.stdout.write(f"rewired groups: {rewired}")
        self.stdout.write(f"deleted zero supplies: {deleted}")
        self.stdout.write("=== END PHASE A ===\n")

    # ============================================================
    # PHASE B: reconcile to WS (WS is truth)
    # ============================================================
    def _phase_reconcile(
        self,
        *,
        apply: bool,
        adj_date: datetime.date,
        min_ws_qty: int,
        only_warehouse_id: int | None,
        only_stock_id: int | None,
        limit: int | None,
    ):
        self.stdout.write("=== PHASE B: ALIGN StockSupply availability to WarehouseStock.quantity (WS is truth) ===")

        qs = (
            WarehouseStock.objects
            .select_related("warehouse", "stock", "stock__stock_type")
            .filter(quantity__gte=min_ws_qty)
            .order_by("warehouse_id", "stock_id", "id")
        )
        if only_warehouse_id:
            qs = qs.filter(warehouse_id=int(only_warehouse_id))
        if only_stock_id:
            qs = qs.filter(stock_id=int(only_stock_id))
        if limit:
            qs = qs[:limit]

        total = qs.count()
        self.stdout.write(f"rows = {total} (min_ws_qty={min_ws_qty})")

        changed = 0

        for idx, ws in enumerate(qs, start=1):
            name = ws.stock.name
            st = ws.stock.stock_type
            ws_qty = int(ws.quantity)

            supplies = list(
                StockSupply.objects
                .filter(name=name, stock_type=st)
                .order_by("date", "id")
            )
            total_available = sum(int(s.available_quantity()) for s in supplies)

            if total_available == ws_qty:
                continue

            diff = ws_qty - total_available  # dodatni = brakuje, ujemny = za dużo

            wh = ws.warehouse.name if ws.warehouse_id else f"warehouse#{ws.warehouse_id}"
            self.stdout.write("")
            self.stdout.write(f"[{idx}/{total}] WS id={ws.id} | {wh} | {name}")
            self.stdout.write(f"  WS.quantity = {ws_qty} | supplies_available = {total_available} | diff = {diff}")

            if not apply:
                self.stdout.write("  DRY-RUN: would apply adjustment to supplies only (WS unchanged).")
                continue

            with transaction.atomic():
                ws_locked = WarehouseStock.objects.select_for_update().get(pk=ws.id)
                supplies_locked = list(
                    StockSupply.objects
                    .select_for_update()
                    .filter(name=name, stock_type=st)
                    .order_by("date", "id")
                )
                total_available_locked = sum(int(s.available_quantity()) for s in supplies_locked)
                diff_locked = int(ws_locked.quantity) - total_available_locked

                if diff_locked == 0:
                    continue

                if diff_locked > 0:
                    # brakuje availability -> dodaj adjustment StockSupply (value=0)
                    self._apply_add_supply(ws_locked, diff_locked, adj_date)
                    # opcjonalnie: historia (informacyjna) – WS nie zmieniamy, ale można zostawić ślad:
                    WarehouseStockHistory.objects.create(
                        warehouse_stock=ws_locked,
                        quantity_before=int(ws_locked.quantity),
                        quantity_after=int(ws_locked.quantity),
                        date=adj_date,
                        sell=None,
                        stock_supply=None,
                        order_settlement=None,
                        assembly=None,
                    )
                else:
                    # za dużo availability -> skonsumuj nadmiar adjustment sell (value=0)
                    self._apply_consume_supplies(ws_locked, supplies_locked, -diff_locked, adj_date)
                    WarehouseStockHistory.objects.create(
                        warehouse_stock=ws_locked,
                        quantity_before=int(ws_locked.quantity),
                        quantity_after=int(ws_locked.quantity),
                        date=adj_date,
                        sell=None,
                        stock_supply=None,
                        order_settlement=None,
                        assembly=None,
                    )

            changed += 1

        self.stdout.write("\n=== PHASE B SUMMARY ===")
        self.stdout.write(f"items adjusted: {changed}")
        self.stdout.write("=== END PHASE B ===")

    # ============================================================
    # Helpers (copied/compatible with your reconcile style)
    # ============================================================
    def _apply_add_supply(self, ws: WarehouseStock, qty_add: int, date: datetime.date):
        ss = StockSupply.objects.create(
            stock_type=ws.stock.stock_type,
            name=ws.stock.name,
            date=date,
            quantity=int(qty_add),
            value=Decimal("0.00"),
            used=False,
            delivery_item=None,
        )
        return ss

    def _apply_consume_supplies(self, ws: WarehouseStock, supplies: list, qty_consume: int, date: datetime.date):
        adj_sell = ProductSell3.objects.create(
            customer=None,
            customer_alter_name="INVENTORY_ADJUSTMENT_ALIGN_TO_WS",
            product=getattr(ws.stock, "product", None),
            stock=ws.stock,
            warehouse_stock=ws,
            order=None,
            quantity=int(qty_consume),
            price=Decimal("0.00"),
            date=date,
        )

        remaining = int(qty_consume)
        for s in supplies:
            if remaining <= 0:
                break
            avail = int(s.available_quantity())
            if avail <= 0:
                try:
                    s.refresh_used_flag(save=True)
                except Exception:
                    pass
                continue

            take = min(avail, remaining)
            StockSupplySell.objects.create(
                stock_supply=s,
                sell=adj_sell,
                quantity=int(take),
            )
            remaining -= take

            try:
                s.refresh_used_flag(save=True)
            except Exception:
                pass

        if remaining > 0:
            raise ValidationError(f"ALIGN consume failed: missing={remaining} (supplies availability inconsistency)")

        return adj_sell
