from __future__ import annotations

import datetime
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import F, IntegerField, ExpressionWrapper


class Command(BaseCommand):
    help = (
        "Rollback OrderSettlement from a given date (default 2026-01-01):\n"
        "- restores WarehouseStock.quantity using WarehouseStockHistory deltas for that settlement\n"
        "- deletes WarehouseStockHistory rows linked to order_settlement\n"
        "- deletes StockSupplySettlement rows linked to settlement\n"
        "- deletes OrderSettlement\n"
        "Default is DRY RUN. Use --commit to apply."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--from-date",
            type=str,
            default="2026-01-01",
            help="Rollback settlements with settlement_date >= FROM_DATE (YYYY-MM-DD). Default: 2026-01-01",
        )
        parser.add_argument(
            "--commit",
            action="store_true",
            help="Apply changes. Without this flag it runs in dry-run mode.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Limit number of settlements processed (newest first). Useful for testing.",
        )
        parser.add_argument(
            "--audit",
            action="store_true",
            help="Print per-history-row deltas for inspection.",
        )

    def handle(self, *args, **options):
        from_date = self._parse_date(options["from_date"])
        commit = bool(options["commit"])
        limit = options["limit"]
        audit = bool(options["audit"])
        dry_run = not commit

        from warehouse.models import (
            OrderSettlement,
            StockSupplySettlement,
            WarehouseStock,
            WarehouseStockHistory,
        )

        qs = (
            OrderSettlement.objects
            .filter(settlement_date__gte=from_date)
            .select_related("order", "material")
            .order_by("-settlement_date", "-id")
        )
        if limit:
            qs = qs[:limit]

        total = qs.count()

        self.stdout.write("")
        self.stdout.write("=== ROLLBACK ORDER SETTLEMENTS ===")
        self.stdout.write(f"FROM DATE: {from_date.isoformat()}")
        self.stdout.write(f"TOTAL SETTLEMENTS: {total}")
        self.stdout.write(f"MODE: {'COMMIT' if commit else 'DRY RUN'}")
        self.stdout.write("")

        if total == 0:
            self.stdout.write("Nothing to do.")
            return

        try:
            with transaction.atomic():
                for s in qs:
                    self.stdout.write("=" * 110)
                    self._process_one_settlement(
                        settlement=s,
                        dry_run=dry_run,
                        audit=audit,
                        StockSupplySettlement=StockSupplySettlement,
                        WarehouseStock=WarehouseStock,
                        WarehouseStockHistory=WarehouseStockHistory,
                    )

                self.stdout.write("=" * 110)
                self.stdout.write("DONE.")
                self.stdout.write("")

                if dry_run:
                    raise _DryRunRollback()

        except _DryRunRollback:
            self.stdout.write("DRY RUN: no changes were saved (transaction rolled back).")
            self.stdout.write("")

    def _process_one_settlement(
        self,
        *,
        settlement,
        dry_run: bool,
        audit: bool,
        StockSupplySettlement,
        WarehouseStock,
        WarehouseStockHistory,
    ):
        order_id = getattr(settlement, "order_id", None)
        self.stdout.write(
            f"SETTLEMENT #{settlement.id} | date={settlement.settlement_date} | order_id={order_id}"
        )

        sss_qs = StockSupplySettlement.objects.filter(settlement_id=settlement.id)
        hist_qs = WarehouseStockHistory.objects.filter(order_settlement_id=settlement.id)

        self.stdout.write(f"  StockSupplySettlement rows: {sss_qs.count()}")
        self.stdout.write(f"  WarehouseStockHistory rows: {hist_qs.count()}")

        # For each history row: reverse the delta on WarehouseStock.quantity
        # delta = after - before; rollback => ws.quantity = ws.quantity - delta
        for h in hist_qs.select_related("warehouse_stock").order_by("id"):
            delta = int(h.quantity_after) - int(h.quantity_before)

            ws = WarehouseStock.objects.select_for_update().get(pk=h.warehouse_stock_id)
            ws_before = ws.quantity
            ws_after = ws_before - delta

            if ws_after < 0:
                raise CommandError(
                    f"WarehouseStock id={ws.id} would go negative when rolling back settlement {settlement.id}: "
                    f"{ws_before} - ({delta}) = {ws_after} (history_id={h.id})."
                )

            if audit:
                self.stdout.write(
                    f"    HIST id={h.id} | ws_id={ws.id} | {h.quantity_before}->{h.quantity_after} | "
                    f"delta={delta} | WS {ws_before}->{ws_after}"
                )

            if not dry_run:
                ws.quantity = ws_after
                ws.save(update_fields=["quantity"])

        if dry_run:
            self.stdout.write("  Would delete WarehouseStockHistory rows for this settlement.")
            self.stdout.write("  Would delete StockSupplySettlement rows for this settlement.")
            self.stdout.write("  Would delete OrderSettlement.")
            return

        # Delete history and settlements, then the OrderSettlement
        deleted_hist, _ = hist_qs.delete()
        deleted_sss, _ = sss_qs.delete()
        settlement.delete()

        self.stdout.write(f"  Deleted WarehouseStockHistory: {deleted_hist}")
        self.stdout.write(f"  Deleted StockSupplySettlement: {deleted_sss}")
        self.stdout.write("  Deleted OrderSettlement.")

    def _parse_date(self, s: str) -> datetime.date:
        try:
            y, m, d = map(int, s.split("-"))
            return datetime.date(y, m, d)
        except Exception:
            raise CommandError(f"Invalid date: {s}. Expected YYYY-MM-DD.")


class _DryRunRollback(Exception):
    pass
