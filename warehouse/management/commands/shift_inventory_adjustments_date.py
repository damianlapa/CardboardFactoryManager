import datetime
from django.core.management.base import BaseCommand
from django.db import transaction

from warehouse.models import (
    ProductSell3,
    WarehouseStockHistory,
    StockSupplySell,
)


class Command(BaseCommand):
    help = (
        "Shift date for all INVENTORY_ADJUSTMENT_RECONCILE sells and related records.\n"
        "Default is DRY-RUN; use --apply to write changes."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            default="2025-12-31",
            help="Target date YYYY-MM-DD (default: 2025-12-31)",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply changes (default dry-run).",
        )

    def handle(self, *args, **opts):
        apply = bool(opts["apply"])
        target_date = datetime.date.fromisoformat(opts["date"])

        sells_qs = ProductSell3.objects.filter(
            customer_alter_name="INVENTORY_ADJUSTMENT_RECONCILE"
        )

        count = sells_qs.count()

        self.stdout.write("=== SHIFT INVENTORY ADJUSTMENT DATES ===")
        self.stdout.write(f"target_date = {target_date}")
        self.stdout.write(f"mode        = {'APPLY' if apply else 'DRY-RUN'}")
        self.stdout.write(f"sells found = {count}")

        if count == 0:
            self.stdout.write("Nothing to do.")
            return

        # preview
        for s in sells_qs.order_by("id")[:10]:
            self.stdout.write(
                f"SELL id={s.id} old_date={s.date} qty={s.quantity} ws_id={s.warehouse_stock_id}"
            )
        if count > 10:
            self.stdout.write("...")

        # related counts preview
        hist_cnt = WarehouseStockHistory.objects.filter(sell__in=sells_qs).count()
        sss_cnt = StockSupplySell.objects.filter(sell__in=sells_qs).count()
        self.stdout.write(f"related WarehouseStockHistory = {hist_cnt}")
        self.stdout.write(f"related StockSupplySell       = {sss_cnt}")

        if not apply:
            self.stdout.write("\nDRY-RUN only. Re-run with --apply to execute.")
            return

        with transaction.atomic():
            updated_sells = sells_qs.update(date=target_date)

            # history linked to sells
            hist_updated = WarehouseStockHistory.objects.filter(
                sell__in=sells_qs
            ).update(date=target_date)

            # StockSupplySell has no date field -> nothing to update here.
            # It will “follow” sell.date via relation.

        self.stdout.write(self.style.SUCCESS(
            f"UPDATED:\n"
            f"- ProductSell3          : {updated_sells}\n"
            f"- WarehouseStockHistory : {hist_updated}\n"
            f"- StockSupplySell       : {sss_cnt} (no direct date field; uses sell.date)\n"
        ))
