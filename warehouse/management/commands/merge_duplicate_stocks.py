from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count

from warehouse.models import Stock, WarehouseStock, BOMPart


class Command(BaseCommand):
    help = "Merge duplicate Stock records by (name, stock_type)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be merged, without modifying the database.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Limit number of duplicate groups to process (for testing).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        limit = options["limit"]

        groups = (
            Stock.objects
            .values("name", "stock_type_id")
            .annotate(c=Count("id"))
            .filter(c__gt=1)
            .order_by("-c", "name")
        )

        if limit:
            groups = groups[:limit]

        if not groups:
            self.stdout.write(self.style.SUCCESS("No duplicate Stock records found."))
            return

        self.stdout.write(
            self.style.WARNING(
                f"Found {groups.count()} duplicate Stock groups."
            )
        )

        for g in groups:
            name = g["name"]
            stock_type_id = g["stock_type_id"]

            stocks = list(
                Stock.objects
                .filter(name=name, stock_type_id=stock_type_id)
                .order_by("id")
            )

            keep = stocks[0]
            others = stocks[1:]

            ws_refs = WarehouseStock.objects.filter(stock__in=others).count()
            bom_refs = BOMPart.objects.filter(part__in=others).count()

            self.stdout.write(
                f"\nStock '{name}' (stock_type_id={stock_type_id})"
            )
            self.stdout.write(
                f"  KEEP:  id={keep.id}"
            )
            self.stdout.write(
                f"  MERGE: ids={[s.id for s in others]}"
            )
            self.stdout.write(
                f"  refs: WarehouseStock={ws_refs}, BOMPart={bom_refs}"
            )

            if dry_run:
                continue

            # ---- FK updates ----
            WarehouseStock.objects.filter(stock__in=others).update(stock=keep)
            BOMPart.objects.filter(part__in=others).update(part=keep)

            # ---- delete duplicates ----
            Stock.objects.filter(id__in=[s.id for s in others]).delete()

        if dry_run:
            self.stdout.write(
                self.style.WARNING("\nDRY RUN complete. No changes were made.")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS("\nMerge complete.")
            )
