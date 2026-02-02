from django.core.management.base import BaseCommand
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Sum

from warehouse.models import (
    StockSupply,
    StockSupplySell,
    StockSupplySettlement,
    WarehouseStockHistory,
)


class Command(BaseCommand):
    help = (
        "Remove duplicate StockSupply rows with value=0 when another supply "
        "with the same (name, stock_type) has value > 0.\n"
        "Only removes supplies that are completely unused.\n"
        "Default is DRY-RUN; use --apply to delete."
    )

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Apply deletions (default dry-run).")
        parser.add_argument("--limit", type=int, default=0, help="Limit number of supplies to delete (0=no limit).")
        parser.add_argument("--verbose", action="store_true", help="Print every affected StockSupply.")

    def handle(self, *args, **opts):
        apply = bool(opts["apply"])
        limit = int(opts["limit"]) or None
        verbose = bool(opts["verbose"])

        self.stdout.write("=== REMOVE ZERO-VALUE STOCKSUPPLY DUPLICATES ===")
        self.stdout.write(f"mode = {'APPLY' if apply else 'DRY-RUN'}")

        # 1) znajdź grupy (name, stock_type), gdzie jest mix value=0 i value>0
        groups = (
            StockSupply.objects
            .values("name", "stock_type")
            .annotate(
                total=Count("id"),
                zero_value=Count("id", filter={"value": 0}),
                positive_value=Count("id", filter={"value__gt": 0}),
            )
            .filter(zero_value__gt=0, positive_value__gt=0)
        )

        if not groups:
            self.stdout.write("No mixed (value=0 / value>0) duplicate groups found.")
            return

        to_delete_ids = []

        for g in groups:
            name = g["name"]
            st = g["stock_type"]

            zero_supplies = (
                StockSupply.objects
                .filter(name=name, stock_type=st, value=0)
                .order_by("date", "id")
            )

            for ss in zero_supplies:
                # sprawdzamy czy supply jest całkowicie nieużywany
                used = (
                    StockSupplySell.objects.filter(stock_supply=ss).exists()
                    or StockSupplySettlement.objects.filter(stock_supply=ss).exists()
                    or WarehouseStockHistory.objects.filter(stock_supply=ss).exists()
                )
                if used:
                    continue

                to_delete_ids.append(ss.id)
                if verbose:
                    self.stdout.write(
                        f"DELETE CANDIDATE ss#{ss.id} | {ss.date} | {ss.name} | qty={ss.quantity} | value=0"
                    )

                if limit and len(to_delete_ids) >= limit:
                    break

            if limit and len(to_delete_ids) >= limit:
                break

        if not to_delete_ids:
            self.stdout.write("No removable zero-value duplicates found.")
            return

        self.stdout.write(f"\nFound {len(to_delete_ids)} StockSupply rows to delete.")

        if not apply:
            self.stdout.write("DRY-RUN only. Use --apply to delete.")
            return

        # APPLY
        with transaction.atomic():
            deleted, _ = StockSupply.objects.filter(id__in=to_delete_ids).delete()

        self.stdout.write(self.style.SUCCESS(f"DELETED {deleted} StockSupply rows."))
