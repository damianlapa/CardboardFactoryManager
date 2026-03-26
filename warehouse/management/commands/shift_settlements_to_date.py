import datetime
from typing import List, Set

from django.core.management.base import BaseCommand
from django.db import transaction

from warehouse.models import (
    WarehouseStock,
    WarehouseStockHistory,
    OrderSettlement,
    StockSupply,
)
from warehouse.services.stock_moves import rebuild_ws_history_from_date


def parse_ids(csv: str) -> List[int]:
    parts = [p.strip() for p in csv.split(",") if p.strip()]
    return [int(p) for p in parts]


class Command(BaseCommand):
    help = (
        "Jednorazowo przesuwa wskazane OrderSettlementy (i powiązane ruchy historii + StockSupply) na target_date "
        "i robi rebuild dotkniętych WarehouseStock od tej daty."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--settlement-ids",
            type=str,
            required=True,
            help="Lista ID settlementów, np. 2991,2992",
        )
        parser.add_argument(
            "--target-date",
            type=str,
            required=True,
            help="YYYY-MM-DD (np. 2026-01-22)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Tylko pokaż co zrobi, bez zapisu.",
        )
        parser.add_argument(
            "--rebuild-from-date",
            type=str,
            default=None,
            help="Jeśli chcesz rebuild od innej daty niż target_date (opcjonalnie).",
        )

    @transaction.atomic
    def handle(self, *args, **opts):
        settlement_ids = parse_ids(opts["settlement_ids"])
        target_date = datetime.date.fromisoformat(opts["target_date"])
        dry = opts["dry_run"]
        rebuild_from = datetime.date.fromisoformat(opts["rebuild_from_date"]) if opts["rebuild_from_date"] else target_date

        self.stdout.write("=== SHIFT SETTLEMENTS TO DATE ===")
        self.stdout.write(f"settlement_ids={settlement_ids}")
        self.stdout.write(f"target_date={target_date}")
        self.stdout.write(f"rebuild_from={rebuild_from}")
        self.stdout.write(f"mode={'DRY-RUN' if dry else 'APPLY'}")
        self.stdout.write("")

        # 1) Pobierz settlements
        settlements = list(OrderSettlement.objects.select_for_update().filter(id__in=settlement_ids))
        found_ids = sorted([s.id for s in settlements])
        missing = sorted(set(settlement_ids) - set(found_ids))
        if missing:
            raise ValueError(f"Missing OrderSettlement IDs: {missing}")

        # 2) Zbierz historie dotknięte settlementami
        hist_qs = WarehouseStockHistory.objects.filter(order_settlement_id__in=settlement_ids)

        hist_count = hist_qs.count()
        affected_ws_ids: List[int] = list(hist_qs.values_list("warehouse_stock_id", flat=True).distinct())

        # 3) Zbierz wszystkie StockSupply powiązane z tymi historiami (jeśli są)
        supply_ids: Set[int] = set(
            x for x in hist_qs.values_list("stock_supply_id", flat=True).distinct() if x
        )

        self.stdout.write(f"History rows to shift: {hist_count}")
        self.stdout.write(f"Affected WS count: {len(affected_ws_ids)}")
        self.stdout.write(f"Related StockSupply IDs: {sorted(supply_ids) if supply_ids else 'none'}")
        self.stdout.write("")

        # Podgląd
        for s in settlements:
            self.stdout.write(f"OrderSettlement#{s.id}: {s.settlement_date} -> {target_date}")

        if supply_ids:
            for ss in StockSupply.objects.filter(id__in=supply_ids).only("id", "date"):
                self.stdout.write(f"StockSupply#{ss.id}: {ss.date} -> {target_date}")

        self.stdout.write("")
        if dry:
            self.stdout.write("DRY-RUN: no changes applied.")
            self.stdout.write("=== END ===")
            return

        # 4) Apply updates
        OrderSettlement.objects.filter(id__in=settlement_ids).update(settlement_date=target_date)

        if supply_ids:
            StockSupply.objects.select_for_update().filter(id__in=supply_ids).update(date=target_date)

        hist_qs.update(date=target_date)

        # 5) Rebuild dotkniętych WS od rebuild_from
        self.stdout.write("Rebuilding affected WS histories...")
        for ws_id in affected_ws_ids:
            ws = WarehouseStock.objects.select_for_update().get(id=ws_id)
            rebuild_ws_history_from_date(ws=ws, from_date=rebuild_from)

        self.stdout.write(self.style.SUCCESS("APPLIED: shifted settlements + related history/supplies and rebuilt WS histories."))
        self.stdout.write("=== END ===")
