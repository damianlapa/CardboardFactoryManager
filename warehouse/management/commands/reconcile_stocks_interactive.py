import datetime
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from warehouse.models import (
    WarehouseStock,
    StockSupply,
    StockSupplySell,
    ProductSell3,
    WarehouseStockHistory,
)


class Command(BaseCommand):
    help = (
        "Interactive reconcile of WarehouseStock with StockSupply availability.\n"
        "For each non-zero WarehouseStock, asks user for real quantity.\n"
        "Then adjusts supplies (add adjustment supply or consume via adjustment sell) "
        "so that FIFO stays consistent.\n"
        "Default is DRY-RUN; use --apply to write changes."
    )

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Apply changes (default dry-run).")
        parser.add_argument("--only-warehouse-id", type=int, default=None, help="Limit to one warehouse_id.")
        parser.add_argument("--only-stock-id", type=int, default=None, help="Limit to one stock_id.")
        parser.add_argument("--min-ws-qty", type=int, default=1, help="Process WarehouseStock with quantity >= this.")
        parser.add_argument("--date", default=None, help="Date for adjustments YYYY-MM-DD (default: today).")
        parser.add_argument("--limit", type=int, default=0, help="Limit number of rows (0=no limit).")

    def handle(self, *args, **opts):
        apply = bool(opts["apply"])
        min_ws_qty = int(opts["min_ws_qty"])
        limit = int(opts["limit"]) or None

        if opts["date"]:
            y, m, d = map(int, opts["date"].split("-"))
            adj_date = datetime.date(y, m, d)
        else:
            adj_date = timezone.now().date()

        qs = WarehouseStock.objects.select_related("warehouse", "stock", "stock__stock_type").filter(quantity__gte=min_ws_qty)

        if opts["only_warehouse_id"]:
            qs = qs.filter(warehouse_id=int(opts["only_warehouse_id"]))
        if opts["only_stock_id"]:
            qs = qs.filter(stock_id=int(opts["only_stock_id"]))

        qs = qs.order_by("warehouse_id", "stock_id", "id")
        if limit:
            qs = qs[:limit]

        total = qs.count()
        self.stdout.write("=== RECONCILE STOCKS (INTERACTIVE) ===")
        self.stdout.write(f"mode = {'APPLY' if apply else 'DRY-RUN'}")
        self.stdout.write(f"date = {adj_date}")
        self.stdout.write(f"rows = {total}")
        self.stdout.write("Instructions: enter target qty, blank=skip, 'q'=quit.\n")

        for idx, ws in enumerate(qs, start=1):
            name = ws.stock.name
            wh = ws.warehouse.name if ws.warehouse_id else f"warehouse#{ws.warehouse_id}"
            st = ws.stock.stock_type

            supplies = list(
                StockSupply.objects
                .filter(name=name, stock_type=st)
                .order_by("date", "id")
            )

            total_available = sum(int(s.available_quantity()) for s in supplies)
            ws_qty = int(ws.quantity)

            self.stdout.write("")
            self.stdout.write(f"[{idx}/{total}] WS id={ws.id} | {wh} | {name}")
            self.stdout.write(f"  WS.quantity = {ws_qty}")
            self.stdout.write(f"  Supplies count = {len(supplies)} | total_available(from supplies) = {total_available}")

            # show last few supplies for context
            tail = supplies[-5:] if len(supplies) > 5 else supplies
            if tail:
                self.stdout.write("  Last supplies:")
                for s in tail:
                    self.stdout.write(
                        f"    ss#{s.id} {s.date} qty={int(s.quantity)} avail={int(s.available_quantity())} used={bool(s.used)} value={s.value}"
                    )

            # Ask user
            raw = input("  Target REAL qty (blank=skip, q=quit): ").strip()
            if raw.lower() == "q":
                self.stdout.write("Quit requested.")
                return
            if raw == "":
                continue

            try:
                target = int(raw)
                if target < 0:
                    raise ValueError()
            except Exception:
                self.stdout.write("  ! invalid input (must be integer >= 0). Skipping.")
                continue

            # Difference we must reconcile at SUPPLY level, not WS level
            diff = target - total_available

            if diff == 0:
                self.stdout.write("  OK: supplies already match target. (WS.quantity may still be off; will align if APPLY)")
            elif diff > 0:
                self.stdout.write(f"  Need to ADD availability: +{diff} (will create adjustment StockSupply)")
            else:
                self.stdout.write(f"  Need to CONSUME availability: {diff} (will create adjustment sell and StockSupplySell)")

            confirm = input("  Apply this change for this item? [y/N]: ").strip().lower()
            if confirm != "y":
                self.stdout.write("  Skipped (not confirmed).")
                continue

            if not apply:
                self.stdout.write("  DRY-RUN: not writing changes.")
                continue

            # APPLY per-WS in its own transaction
            with transaction.atomic():
                ws_locked = WarehouseStock.objects.select_for_update().get(pk=ws.id)

                # Recompute under lock
                supplies_locked = list(
                    StockSupply.objects
                    .select_for_update()
                    .filter(name=name, stock_type=st)
                    .order_by("date", "id")
                )
                total_available_locked = sum(int(s.available_quantity()) for s in supplies_locked)
                diff_locked = target - total_available_locked

                if diff_locked > 0:
                    self._apply_add_supply(ws_locked, diff_locked, adj_date)
                elif diff_locked < 0:
                    self._apply_consume_supplies(ws_locked, supplies_locked, -diff_locked, adj_date)
                else:
                    # nothing to do on supplies
                    pass

                # Align WS.quantity to target (this is now consistent with supplies)
                before = int(ws_locked.quantity)
                if before != target:
                    ws_locked.quantity = int(target)
                    ws_locked.save(update_fields=["quantity"])

                    WarehouseStockHistory.objects.create(
                        warehouse_stock=ws_locked,
                        quantity_before=before,
                        quantity_after=int(target),
                        date=adj_date,
                        sell=None,
                        stock_supply=None,
                        order_settlement=None,
                        assembly=None,
                    )

                self.stdout.write("  ✅ Applied.")

        self.stdout.write("\nDONE.")

    def _apply_add_supply(self, ws: WarehouseStock, qty_add: int, date: datetime.date):
        """
        Adds availability by creating a technical StockSupply (value=0).
        """
        ss = StockSupply.objects.create(
            stock_type=ws.stock.stock_type,
            name=ws.stock.name,
            date=date,
            quantity=int(qty_add),
            value=Decimal("0.00"),
            used=False,
            delivery_item=None,
            dimensions=getattr(ws.stock, "dimensions", None) if hasattr(ws.stock, "dimensions") else None,
        )

        # history: increase (linked to stock_supply)
        before = int(ws.quantity)
        after = before + int(qty_add)
        WarehouseStockHistory.objects.create(
            warehouse_stock=ws,
            stock_supply=ss,
            quantity_before=before,
            quantity_after=after,
            date=date,
            sell=None,
            order_settlement=None,
            assembly=None,
        )

        # we do NOT directly change ws.quantity here; final alignment happens in handle()
        return ss

    def _apply_consume_supplies(self, ws: WarehouseStock, supplies: list, qty_consume: int, date: datetime.date):
        """
        Consumes availability FIFO by creating technical sell + StockSupplySell rows.
        """
        # technical adjustment sell
        adj_sell = ProductSell3.objects.create(
            customer=None,
            customer_alter_name="INVENTORY_ADJUSTMENT_RECONCILE",
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
            raise ValidationError(
                f"Reconcile consume failed: not enough available in supplies. missing={remaining}"
            )

        # history: decrease (linked to sell)
        before = int(ws.quantity)
        after = before - int(qty_consume)
        WarehouseStockHistory.objects.create(
            warehouse_stock=ws,
            sell=adj_sell,
            quantity_before=before,
            quantity_after=after,
            date=date,
            stock_supply=None,
            order_settlement=None,
            assembly=None,
        )

        return adj_sell
