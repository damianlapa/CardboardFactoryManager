from __future__ import annotations

import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Model
from django.apps import apps


class Command(BaseCommand):
    help = "Rollback ProductSell3 from 2026-01-01 (delete sells, restore WarehouseStock qty). Default DRY RUN."

    def add_arguments(self, parser):
        parser.add_argument("--from-date", type=str, default="2026-01-01")
        parser.add_argument("--commit", action="store_true", help="Apply changes (otherwise DRY RUN)")
        parser.add_argument("--limit", type=int, default=0, help="Limit number of sells processed (0 = no limit)")
        parser.add_argument("--verbose", action="store_true")

    def _get_model(self, app_label: str, model_name: str) -> Model:
        return apps.get_model(app_label, model_name)

    def _print_model_fields(self, model):
        fields = []
        for f in model._meta.get_fields():
            fields.append(f"{f.name} ({f.__class__.__name__})")
        self.stdout.write(f"{model.__name__} fields: " + ", ".join(fields))

    def _find_fk_field_name(self, model, target_model) -> str | None:
        """
        Returns name of FK field on `model` that points to `target_model` if exists.
        """
        for f in model._meta.get_fields():
            if f.is_relation and f.many_to_one and getattr(f, "related_model", None) == target_model:
                return f.name
        return None

    def _maybe_restore_stock_supply(self, sss, qty: int, verbose: bool):
        """
        Best-effort: if StockSupply has a 'quantity_left'/'available' style field,
        increment it back. If we can't detect, we only delete StockSupplySell.
        """
        ss = getattr(sss, "stock_supply", None)
        if not ss:
            return

        # Try common field names (adjust if you know the real one)
        candidates = ["quantity_left", "qty_left", "available_quantity", "available_qty", "remaining_quantity", "remaining_qty"]
        for name in candidates:
            if hasattr(ss, name):
                old = getattr(ss, name) or 0
                setattr(ss, name, old + qty)
                ss.save(update_fields=[name])
                if verbose:
                    print(f"    Restored StockSupply.{name}: {old} -> {old + qty}")
                return

        # If nothing matched, do nothing (we don't want to corrupt unknown logic)
        if verbose:
            print("    StockSupply restore skipped (no known remaining/available field detected).")

    def handle(self, *args, **options):
        from_date = datetime.date.fromisoformat(options["from_date"])
        commit = options["commit"]
        limit = options["limit"]
        verbose = options["verbose"]

        # Import your real models (adjust app label if different)
        ProductSell3 = self._get_model("warehouse", "ProductSell3")
        StockSupplySell = self._get_model("warehouse", "StockSupplySell")
        WarehouseStock = self._get_model("warehouse", "WarehouseStock")

        # Optional (only if exists in your app)
        WarehouseStockHistory = None
        try:
            WarehouseStockHistory = self._get_model("warehouse", "WarehouseStockHistory")
        except Exception:
            pass

        self.stdout.write("=== INTROSPECTION ===")
        self._print_model_fields(ProductSell3)
        self._print_model_fields(StockSupplySell)
        self._print_model_fields(WarehouseStock)
        if WarehouseStockHistory:
            self._print_model_fields(WarehouseStockHistory)

        hist_fk_name = None
        if WarehouseStockHistory:
            hist_fk_name = self._find_fk_field_name(WarehouseStockHistory, ProductSell3)
            if hist_fk_name:
                self.stdout.write(f"WarehouseStockHistory FK to ProductSell3 detected: {hist_fk_name}")
            else:
                self.stdout.write("WarehouseStockHistory: no FK to ProductSell3 detected (auto-delete history will be skipped).")

        qs = (
            ProductSell3.objects
            .select_related("warehouse_stock", "order")
            .filter(date__gte=from_date)
            .order_by("-date", "-id")
        )
        if limit and limit > 0:
            qs = qs[:limit]

        sells = list(qs)
        self.stdout.write(f"\n=== SELLS FROM {from_date} ===")
        self.stdout.write(f"Total sells: {len(sells)}")
        self.stdout.write(f"MODE: {'COMMIT' if commit else 'DRY RUN'}\n")

        @transaction.atomic
        def process_one(sell):
            self.stdout.write("=" * 90)
            self.stdout.write(f"SELL id={sell.id} | date={sell.date} | qty={sell.quantity}")
            ws = sell.warehouse_stock
            self.stdout.write(f"  warehouse_stock_id: {getattr(ws, 'id', None)}")

            # FIFO rows
            fifo_rows = list(StockSupplySell.objects.select_related("stock_supply").filter(sell=sell))
            self.stdout.write("  StockSupplySell:")
            if not fifo_rows:
                self.stdout.write("    (BRAK)")
            else:
                total_fifo = 0
                for r in fifo_rows:
                    self.stdout.write(f"    id={r.id} stock_supply_id={r.stock_supply_id} qty={r.quantity}")
                    total_fifo += int(r.quantity)
                self.stdout.write(f"    FIFO total qty: {total_fifo}")

            # Restore WarehouseStock quantity
            if not ws:
                self.stdout.write("  WARNING: sell has no warehouse_stock; skipping qty restore.")
            else:
                old_qty = int(getattr(ws, "quantity", 0) or 0)
                new_qty = old_qty + int(sell.quantity or 0)
                self.stdout.write(f"  WarehouseStock.quantity: {old_qty} -> {new_qty}")
                if commit:
                    # Lock row to avoid race
                    ws_locked = WarehouseStock.objects.select_for_update().get(pk=ws.pk)
                    ws_locked.quantity = new_qty
                    ws_locked.save(update_fields=["quantity"])

            # Restore StockSupply remaining qty (best-effort) then delete FIFO rows
            if fifo_rows and commit:
                for r in fifo_rows:
                    try:
                        self._maybe_restore_stock_supply(r, int(r.quantity), verbose=verbose)
                    except Exception as e:
                        self.stdout.write(f"  WARNING: StockSupply restore failed for StockSupplySell id={r.id}: {e}")
                StockSupplySell.objects.filter(id__in=[r.id for r in fifo_rows]).delete()
                self.stdout.write(f"  Deleted StockSupplySell rows: {len(fifo_rows)}")
            elif fifo_rows:
                self.stdout.write(f"  Would delete StockSupplySell rows: {len(fifo_rows)}")

            # Delete WarehouseStockHistory rows linked to sell (if FK exists)
            if WarehouseStockHistory and hist_fk_name:
                hist_qs = WarehouseStockHistory.objects.filter(**{hist_fk_name: sell})
                cnt = hist_qs.count()
                if cnt:
                    self.stdout.write(f"  WarehouseStockHistory linked rows: {cnt}")
                    if commit:
                        hist_qs.delete()
                        self.stdout.write("  Deleted linked WarehouseStockHistory rows.")
                else:
                    self.stdout.write("  WarehouseStockHistory linked rows: 0")

            # Finally delete sell
            if commit:
                sell.delete()
                self.stdout.write("  Deleted ProductSell3.")
            else:
                self.stdout.write("  Would delete ProductSell3.")

        # Process
        for sell in sells:
            if commit:
                process_one(sell)
            else:
                # In DRY RUN keep it non-atomic so it doesn't hold locks
                process_one.__wrapped__(sell)  # type: ignore

        self.stdout.write("\nDONE.")
