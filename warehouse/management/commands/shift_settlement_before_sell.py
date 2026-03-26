import datetime
from django.core.management.base import BaseCommand
from django.db import transaction

from warehouse.models import (
    WarehouseStock,
    WarehouseStockHistory,
    ProductSell3,
    OrderSettlement,
    StockSupply,
)
from warehouse.services.stock_moves import rebuild_ws_history_from_date


class Command(BaseCommand):
    help = (
        "Jednorazowo przesuwa settlement (i powiązane ruchy/historię) na dzień przed wskazaną sprzedażą "
        "dla konkretnego WarehouseStock."
    )

    def add_arguments(self, parser):
        parser.add_argument("--ws-id", type=int, required=True, help="WarehouseStock id (np. 5041)")
        parser.add_argument("--sell-id", type=int, required=True, help="ProductSell3 id (np. 2074)")
        parser.add_argument("--dry-run", action="store_true", help="Tylko pokaż co zrobi, bez zapisu.")
        parser.add_argument(
            "--prefer-settlement-id",
            type=int,
            default=None,
            help="Jeśli znasz settlement_id (np. 2826), wymuś użycie tego ID.",
        )

    @transaction.atomic
    def handle(self, *args, **opts):
        ws_id = opts["ws_id"]
        sell_id = opts["sell_id"]
        dry = opts["dry_run"]
        prefer_settlement_id = opts["prefer_settlement_id"]

        ws = WarehouseStock.objects.select_for_update().select_related("warehouse", "stock").get(id=ws_id)
        sell = ProductSell3.objects.get(id=sell_id)

        target_date = sell.date - datetime.timedelta(days=1)

        self.stdout.write(f"=== SHIFT SETTLEMENT BEFORE SELL ===")
        self.stdout.write(f"WS id={ws.id} | wh='{ws.warehouse.name}' | stock='{ws.stock.name}'")
        self.stdout.write(f"Sell id={sell.id} date={sell.date} -> target_date={target_date}")
        self.stdout.write(f"mode={'DRY-RUN' if dry else 'APPLY'}")
        self.stdout.write("")

        # 1) znajdź wpis historii odpowiadający sprzedaży w tym WS
        sell_hist = (
            WarehouseStockHistory.objects
            .filter(warehouse_stock=ws, sell_id=sell.id)
            .order_by("date", "id")
            .first()
        )
        if not sell_hist:
            raise ValueError(f"No WarehouseStockHistory row for WS id={ws.id} with sell_id={sell.id}")

        self.stdout.write(f"Sell history row: H#{sell_hist.id} date={sell_hist.date} delta={sell_hist.delta}")

        # 2) znajdź "przychód" (delta>0) po tej sprzedaży, powiązany z settlementem
        #    (w Twoim case to jest row z settle=2826, supply=6841)
        candidate_qs = (
            WarehouseStockHistory.objects
            .filter(warehouse_stock=ws, date__gte=sell_hist.date, delta__gt=0)
            .exclude(order_settlement_id__isnull=True)
            .order_by("date", "id")
        )
        if prefer_settlement_id:
            candidate_qs = candidate_qs.filter(order_settlement_id=prefer_settlement_id)

        in_hist = candidate_qs.first()
        if not in_hist:
            raise ValueError(
                "No candidate IN history row found after sell row "
                "(delta>0 with order_settlement). Provide --prefer-settlement-id if needed."
            )

        settlement_id = in_hist.order_settlement_id
        supply_id = in_hist.stock_supply_id

        self.stdout.write(
            f"Chosen IN history row: H#{in_hist.id} date={in_hist.date} delta={in_hist.delta} "
            f"settlement_id={settlement_id} supply_id={supply_id}"
        )
        self.stdout.write("")

        settlement = OrderSettlement.objects.select_for_update().get(id=settlement_id)

        # 3) zbierz wszystkie historię, które mają ten settlement i/lub tę partię
        hist_to_shift = WarehouseStockHistory.objects.filter(order_settlement_id=settlement_id)
        if supply_id:
            hist_to_shift = hist_to_shift | WarehouseStockHistory.objects.filter(stock_supply_id=supply_id)
        hist_to_shift = hist_to_shift.distinct()

        # Dotknięte WS (mogą być różne magazyny)
        affected_ws_ids = list(hist_to_shift.values_list("warehouse_stock_id", flat=True).distinct())

        self.stdout.write(f"Will shift OrderSettlement#{settlement_id} settlement_date: {settlement.settlement_date} -> {target_date}")
        if supply_id:
            ss = StockSupply.objects.get(id=supply_id)
            self.stdout.write(f"Will shift StockSupply#{supply_id} date: {ss.date} -> {target_date}")
        self.stdout.write(f"History rows to shift: {hist_to_shift.count()} (affected WS count: {len(affected_ws_ids)})")
        self.stdout.write("")

        if dry:
            self.stdout.write("DRY-RUN: no changes applied.")
            self.stdout.write("=== END ===")
            return

        # 4) apply: update dates
        settlement.settlement_date = target_date
        settlement.save(update_fields=["settlement_date"])

        if supply_id:
            ss = StockSupply.objects.select_for_update().get(id=supply_id)
            ss.date = target_date
            ss.save(update_fields=["date"])

        hist_to_shift.update(date=target_date)

        # 5) rebuild dotkniętych WS od target_date
        self.stdout.write("Rebuilding affected WS histories...")
        for awsid in affected_ws_ids:
            aws = WarehouseStock.objects.select_for_update().get(id=awsid)
            rebuild_ws_history_from_date(ws=aws, from_date=target_date)

        self.stdout.write(self.style.SUCCESS("APPLIED: settlement + related history shifted and WS histories rebuilt."))
        self.stdout.write("=== END ===")
