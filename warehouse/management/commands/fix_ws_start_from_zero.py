from django.core.management.base import BaseCommand
from django.db import transaction

from warehouse.models import WarehouseStock, WarehouseStockHistory
from warehouse.services.stock_moves import rebuild_ws_history_from_date


class Command(BaseCommand):
    help = (
        "Fix WarehouseStockHistory so that the first record starts from 0 "
        "(rebuild full history for WS where first quantity_before != 0)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only show what would be fixed, do not change the database.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Limit number of WS to process (0 = no limit).",
        )
        parser.add_argument(
            "--ws-id",
            type=int,
            nargs="*",
            default=None,
            help="Process only selected WarehouseStock ids (space separated).",
        )

    def handle(self, *args, **options):
        dry_run = bool(options["dry_run"])
        limit = int(options["limit"] or 0)
        only_ids = options["ws_id"]

        self.stdout.write("\n=== FIX WS START FROM ZERO ===\n")

        qs = WarehouseStock.objects.select_related("warehouse", "stock").all()
        if only_ids:
            qs = qs.filter(id__in=only_ids)

        candidates = []
        checked = 0

        for ws in qs:
            checked += 1
            first = (
                WarehouseStockHistory.objects
                .filter(warehouse_stock=ws)
                .order_by("date", "id")
                .first()
            )
            if not first:
                continue

            if int(first.quantity_before) != 0:
                candidates.append((ws, first))

        if limit and len(candidates) > limit:
            candidates = candidates[:limit]

        self.stdout.write(f"Checked WS: {checked}")
        self.stdout.write(f"Candidates to fix: {len(candidates)}")
        self.stdout.write(f"Mode: {'DRY-RUN' if dry_run else 'APPLY'}\n")

        if not candidates:
            self.stdout.write("Nothing to fix.\n=== END ===\n")
            return

        ok = 0
        failed = 0

        for i, (ws, first) in enumerate(candidates, start=1):
            line = (
                f"[{i}/{len(candidates)}] WS_ID={ws.id} | "
                f"{ws.warehouse.name} | {ws.stock.name} | "
                f"first_date={first.date} before={first.quantity_before} after={first.quantity_after}"
            )
            self.stdout.write(line)

            if dry_run:
                continue

            try:
                # Osobna transakcja per WS -> jak jeden padnie, reszta idzie dalej
                with transaction.atomic():
                    rebuild_ws_history_from_date(ws=ws, from_date=None)

                # sanity check: po naprawie pierwszy wpis ma startować od 0
                first2 = (
                    WarehouseStockHistory.objects
                    .filter(warehouse_stock=ws)
                    .order_by("date", "id")
                    .first()
                )

                if not first2 or int(first2.quantity_before) != 0:
                    raise ValueError(
                        f"Sanity check failed: first.quantity_before={getattr(first2, 'quantity_before', None)}"
                    )

                ok += 1
            except Exception as e:
                failed += 1
                self.stdout.write(self.style.ERROR(f"  ERROR WS_ID={ws.id}: {e}"))

        self.stdout.write("\n---- SUMMARY ----")
        self.stdout.write(f"Fixed OK: {ok}")
        self.stdout.write(f"Failed:   {failed}")
        self.stdout.write("\n=== END ===\n")