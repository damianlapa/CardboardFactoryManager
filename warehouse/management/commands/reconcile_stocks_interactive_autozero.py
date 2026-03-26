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
        "Interactive reconcile like reconcile_stocks_interactive, BUT:\n"
        "- if all matching StockSupply have value=0 (sum value == 0), it auto-sets target=0 without prompting.\n"
        "Default is DRY-RUN; use --apply to write changes."
    )

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Apply changes (default dry-run).")
        parser.add_argument("--only-warehouse-id", type=int, default=None, help="Limit to one warehouse_id.")
        parser.add_argument("--only-stock-id", type=int, default=None, help="Limit to one stock_id.")
        parser.add_argument("--min-ws-qty", type=int, default=1, help="Process WarehouseStock with quantity >= this.")
        parser.add_argument("--date", default=None, help="Date for adjustments YYYY-MM-DD (default: today).")
        parser.add_argument("--limit", type=int, default=0, help="Limit number of rows (0=no limit).")
        parser.add_argument("--auto-zero-only", action="store_true",
                            help="Process ONLY auto-zero items (no interactive prompts).")

    def handle(self, *args, **opts):
        apply = bool(opts["apply"])
        min_ws_qty = int(opts["min_ws_qty"])
        limit = int(opts["limit"]) or None
        auto_zero_only = bool(opts["auto_zero_only"])

        if opts["date"]:
            y, m, d = map(int, opts["date"].split("-"))
            adj_date = datetime.date(y, m, d)
        else:
            adj_date = timezone.now().date()

        qs = (
            WarehouseStock.objects
            .select_related("warehouse", "stock", "stock__stock_type")
            .filter(quantity__gte=min_ws_qty)
            .order_by("warehouse_id", "stock_id", "id")
        )

        if opts["only_warehouse_id"]:
            qs = qs.filter(warehouse_id=int(opts["only_warehouse_id"]))
        if opts["only_stock_id"]:
            qs = qs.filter(stock_id=int(opts["only_stock_id"]))

        if limit:
            qs = qs[:limit]

        total = qs.count()
        self.stdout.write("=== RECONCILE STOCKS (AUTOZERO) ===")
        self.stdout.write(f"mode = {'APPLY' if apply else 'DRY-RUN'}")
        self.stdout.write(f"date = {adj_date}")
        self.stdout.write(f"rows = {total}")
        self.stdout.write("Auto-zero rule: if sum(value) == 0 for all matching supplies -> target=0 (no prompt).\n")

        auto_count = 0
        prompt_count = 0
        changed_count = 0

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

            sum_value = Decimal("0.00")
            for s in supplies:
                try:
                    sum_value += Decimal(s.value or 0)
                except Exception:
                    # jeśli value czasem jest None/strange
                    pass

            is_autozero = (len(supplies) > 0 and sum_value == Decimal("0.00"))

            # jeśli nie ma supplies, to NIE auto-zero (bo to może być inny problem) – zostawiamy interaktywnie
            if not supplies:
                is_autozero = False

            if is_autozero:
                auto_count += 1

                # jeśli już jest 0 i supplies dostępne 0 -> skip
                if ws_qty == 0 and total_available == 0:
                    continue

                self.stdout.write("")
                self.stdout.write(f"[{idx}/{total}] AUTOZERO WS id={ws.id} | {wh} | {name}")
                self.stdout.write(f"  WS.quantity = {ws_qty}")
                self.stdout.write(f"  Supplies count = {len(supplies)} | total_available = {total_available} | sum(value)=0 -> target=0")

                if not apply:
                    self.stdout.write("  DRY-RUN: would set target=0 and reconcile supplies.")
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

                    # consume everything available to reach 0
                    if total_available_locked > 0:
                        self._apply_consume_supplies(ws_locked, supplies_locked, total_available_locked, adj_date)

                    # align WS to 0
                    before = int(ws_locked.quantity)
                    if before != 0:
                        ws_locked.quantity = 0
                        ws_locked.save(update_fields=["quantity"])
                        WarehouseStockHistory.objects.create(
                            warehouse_stock=ws_locked,
                            quantity_before=before,
                            quantity_after=0,
                            date=adj_date,
                            sell=None,
                            stock_supply=None,
                            order_settlement=None,
                            assembly=None,
                        )

                changed_count += 1
                continue

            # if only auto-zero mode, skip non-autozero
            if auto_zero_only:
                continue

            # interactive branch
            prompt_count += 1

            self.stdout.write("")
            self.stdout.write(f"[{idx}/{total}] WS id={ws.id} | {wh} | {name}")
            self.stdout.write(f"  WS.quantity = {ws_qty}")
            self.stdout.write(f"  Supplies count = {len(supplies)} | total_available(from supplies) = {total_available} | sum(value)={sum_value}")

            tail = supplies[-5:] if len(supplies) > 5 else supplies
            if tail:
                self.stdout.write("  Last supplies:")
                for s in tail:
                    self.stdout.write(
                        f"    ss#{s.id} {s.date} qty={int(s.quantity)} avail={int(s.available_quantity())} used={bool(s.used)} value={s.value}"
                    )

            raw = input("  Target REAL qty (blank=skip, q=quit): ").strip()
            if raw.lower() == "q":
                self.stdout.write("Quit requested.")
                break
            if raw == "":
                continue

            try:
                target = int(raw)
                if target < 0:
                    raise ValueError()
            except Exception:
                self.stdout.write("  ! invalid input (must be integer >= 0). Skipping.")
                continue

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

            with transaction.atomic():
                ws_locked = WarehouseStock.objects.select_for_update().get(pk=ws.id)
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

            changed_count += 1
            self.stdout.write("  ✅ Applied.")

        self.stdout.write("\n=== SUMMARY ===")
        self.stdout.write(f"autozero items seen   : {auto_count}")
        self.stdout.write(f"interactive prompted  : {prompt_count}")
        self.stdout.write(f"items changed/applied : {changed_count}")
        self.stdout.write("DONE.")

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
        return ss

    def _apply_consume_supplies(self, ws: WarehouseStock, supplies: list, qty_consume: int, date: datetime.date):
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
