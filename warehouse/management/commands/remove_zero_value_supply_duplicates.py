from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count, Q

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
        "Only removes supplies that are completely unused (no sells/settlements/history).\n"
        "Default is DRY-RUN; use --apply to delete."
    )

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Apply deletions (default dry-run).")
        parser.add_argument("--limit", type=int, default=0, help="Limit number of supplies to delete (0=no limit).")
        parser.add_argument("--verbose", action="store_true", help="Print every delete candidate.")
        parser.add_argument("--starts-with", default=None, help="Optional: only names starting with this prefix.")

    def handle(self, *args, **opts):
        apply = bool(opts["apply"])
        limit = int(opts["limit"]) or None
        verbose = bool(opts["verbose"])
        starts_with = opts.get("starts_with")

        self.stdout.write("=== REMOVE ZERO-VALUE STOCKSUPPLY DUPLICATES ===")
        self.stdout.write(f"mode = {'APPLY' if apply else 'DRY-RUN'}")

        base_qs = StockSupply.objects.all()
        if starts_with:
            base_qs = base_qs.filter(name__startswith=starts_with)

        # 1) candidate groups: duplicates by (name, stock_type)
        groups = (
            base_qs.values("name", "stock_type")
            .annotate(total=Count("id"))
            .filter(total__gt=1)
            .order_by("name", "stock_type")
        )

        if not groups.exists():
            self.stdout.write("No duplicate (name, stock_type) groups found.")
            return

        to_delete_ids = []
        groups_checked = 0
        groups_mixed = 0

        for g in groups.iterator(chunk_size=500):
            groups_checked += 1
            name = g["name"]
            st_id = g["stock_type"]

            supplies = list(
                StockSupply.objects
                .filter(name=name, stock_type_id=st_id)
                .only("id", "date", "name", "quantity", "value", "stock_type")
                .order_by("date", "id")
            )

            # is there at least one valuable supply?
            has_value = any(Decimal(s.value or 0) > 0 for s in supplies)
            has_zero = any(Decimal(s.value or 0) == 0 for s in supplies)

            if not (has_value and has_zero):
                continue  # not a mixed group

            groups_mixed += 1

            # delete candidates: value==0 AND completely unused
            for ss in supplies:
                if Decimal(ss.value or 0) != 0:
                    continue

                used = (
                    StockSupplySell.objects.filter(stock_supply_id=ss.id).exists()
                    or StockSupplySettlement.objects.filter(stock_supply_id=ss.id).exists()
                    or WarehouseStockHistory.objects.filter(stock_supply_id=ss.id).exists()
                )
                if used:
                    continue

                to_delete_ids.append(ss.id)
                if verbose:
                    self.stdout.write(
                        f"DELETE CANDIDATE ss#{ss.id} | {ss.date} | st={st_id} | qty={ss.quantity} | value=0 | {ss.name}"
                    )

                if limit and len(to_delete_ids) >= limit:
                    break

            if limit and len(to_delete_ids) >= limit:
                break

        self.stdout.write(f"groups_checked = {groups_checked}")
        self.stdout.write(f"mixed_groups   = {groups_mixed}")
        self.stdout.write(f"delete_candidates = {len(to_delete_ids)}")

        if not to_delete_ids:
            self.stdout.write("No removable zero-value duplicates found.")
            return

        if not apply:
            self.stdout.write("DRY-RUN only. Use --apply to delete.")
            return

        with transaction.atomic():
            deleted, _ = StockSupply.objects.filter(id__in=to_delete_ids).delete()

        self.stdout.write(self.style.SUCCESS(f"DELETED {deleted} StockSupply rows."))
