from __future__ import annotations

import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import F, IntegerField, ExpressionWrapper


class Command(BaseCommand):
    help = (
        "Rollback ProductSell3 from a given date (default 2026-01-01):\n"
        "- deletes StockSupplySell rows for the sell\n"
        "- restores WarehouseStock.quantity (adds sell.quantity)\n"
        "- deletes matching WarehouseStockHistory rows (delta-based match)\n"
        "- deletes ProductSell3\n"
        "Default is DRY RUN. Use --commit to apply."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--from-date",
            type=str,
            default="2026-01-01",
            help="Rollback sells with date >= FROM_DATE (YYYY-MM-DD). Default: 2026-01-01",
        )
        parser.add_argument(
            "--commit",
            action="store_true",
            help="Apply changes. Without this flag it runs in dry-run mode.",
        )
        parser.add_argument(
            "--audit-history",
            action="store_true",
            help="If no matching history rows found for a sell, print nearby history rows for inspection.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Limit number of sells processed (newest first). Useful for testing.",
        )

    def handle(self, *args, **options):
        from_date = self._parse_date(options["from_date"])
        commit = bool(options["commit"])
        audit_history = bool(options["audit_history"])
        limit = options["limit"]

        # --- Import models here to avoid app loading issues ---
        from warehouse.models import (
            ProductSell3,
            StockSupplySell,
            WarehouseStock,
            WarehouseStockHistory,
        )

        dry_run = not commit

        sells_qs = (
            ProductSell3.objects
            .filter(date__gte=from_date)
            .select_related("warehouse_stock", "product", "customer", "order")
            .order_by("-date", "-id")
        )
        if limit:
            sells_qs = sells_qs[:limit]

        total = sells_qs.count()

        self.stdout.write("")
        self.stdout.write("=== ROLLBACK PRODUCTSELL3 ===")
        self.stdout.write(f"FROM DATE: {from_date.isoformat()}")
        self.stdout.write(f"TOTAL SELLS: {total}")
        self.stdout.write(f"MODE: {'COMMIT' if commit else 'DRY RUN'}")
        self.stdout.write("")

        if total == 0:
            self.stdout.write("Nothing to do.")
            return

        try:
            with transaction.atomic():
                for _idx, sell in enumerate(sells_qs, start=1):
                    self.stdout.write("=" * 98)
                    self._process_one_sell(
                        sell=sell,
                        dry_run=dry_run,
                        audit_history=audit_history,
                        StockSupplySell=StockSupplySell,
                        WarehouseStock=WarehouseStock,
                        WarehouseStockHistory=WarehouseStockHistory,
                    )

                self.stdout.write("=" * 98)
                self.stdout.write("DONE.")
                self.stdout.write("")

                if dry_run:
                    raise _DryRunRollback()

        except _DryRunRollback:
            self.stdout.write("DRY RUN: no changes were saved (transaction rolled back).")
            self.stdout.write("")

    def _process_one_sell(
        self,
        *,
        sell,
        dry_run: bool,
        audit_history: bool,
        StockSupplySell,
        WarehouseStock,
        WarehouseStockHistory,
    ):
        # Lock the WarehouseStock row so concurrent operations won't mess quantities
        ws = WarehouseStock.objects.select_for_update().get(pk=sell.warehouse_stock_id)

        qty_before = ws.quantity  # current (post-sell) as in DB right now
        qty_after = qty_before + sell.quantity

        self.stdout.write(
            f"SELL #{sell.id} | date={sell.date} | qty={sell.quantity} | "
            f"warehouse_stock_id={sell.warehouse_stock_id}"
        )

        # 1) StockSupplySell rows (FIFO mapping)
        sss_qs = StockSupplySell.objects.filter(sell_id=sell.id)
        sss_count = sss_qs.count()
        self.stdout.write(f"  StockSupplySell to delete: {sss_count}")

        # 2) WarehouseStockHistory rows that match this sell (delta-based)
        #
        # Szukamy wpisu historii bez powiązań (stock_supply/order_settlement/assembly = NULL)
        # i z deltą dokładnie równą sell.quantity:
        #   quantity_before - quantity_after == sell.quantity
        #
        delta_expr = ExpressionWrapper(
            F("quantity_before") - F("quantity_after"),
            output_field=IntegerField()
        )

        hist_qs = (
            WarehouseStockHistory.objects
            .filter(
                warehouse_stock_id=ws.id,
                date=sell.date,
                stock_supply__isnull=True,
                order_settlement__isnull=True,
                assembly__isnull=True,
            )
            .annotate(delta=delta_expr)
            .filter(delta=sell.quantity)
        )
        hist_count = hist_qs.count()
        self.stdout.write(f"  History matches to delete: {hist_count}")

        # Optional audit if we didn't find matches
        if audit_history and hist_count == 0:
            self.stdout.write("  AUDIT: no exact matching history row found.")
            around = (
                WarehouseStockHistory.objects
                .filter(warehouse_stock_id=ws.id)
                .filter(
                    date__gte=sell.date - datetime.timedelta(days=7),
                    date__lte=sell.date + datetime.timedelta(days=7),
                )
                .order_by("date", "id")
            )[:40]

            if around:
                for h in around:
                    self.stdout.write(
                        "    "
                        f"HIST id={h.id} | date={h.date} | "
                        f"before={h.quantity_before} -> after={h.quantity_after} | "
                        f"stock_supply_id={getattr(h, 'stock_supply_id', None)} | "
                        f"order_settlement_id={getattr(h, 'order_settlement_id', None)} | "
                        f"assembly_id={getattr(h, 'assembly_id', None)}"
                    )
            else:
                self.stdout.write("    (no history rows in +-7 days window)")

        # DRY RUN ends here (we only printed what would happen)
        if dry_run:
            self.stdout.write(f"  WarehouseStock.quantity: {qty_before} -> {qty_after}")
            self.stdout.write("  Would delete ProductSell3.")
            return

        # --- COMMIT (apply changes) ---
        deleted_sss, _ = sss_qs.delete()
        self.stdout.write(f"  Deleted StockSupplySell rows: {deleted_sss}")

        deleted_hist, _ = hist_qs.delete()
        self.stdout.write(f"  Deleted history rows: {deleted_hist}")

        ws.quantity = qty_after
        ws.save(update_fields=["quantity"])
        self.stdout.write(f"  Updated WarehouseStock.quantity: {qty_before} -> {qty_after}")

        sell.delete()
        self.stdout.write("  Deleted ProductSell3.")

    def _parse_date(self, s: str) -> datetime.date:
        try:
            y, m, d = map(int, s.split("-"))
            return datetime.date(y, m, d)
        except Exception:
            raise ValueError(f"Invalid date: {s}. Expected YYYY-MM-DD.")


class _DryRunRollback(Exception):
    """Internal exception to force transaction rollback in dry-run mode."""
    pass
