from django.core.management.base import BaseCommand
from django.db.models import Count

from warehouse.models import StockSupply


class Command(BaseCommand):
    help = "Audit duplicate StockSupply rows grouped by (date, name, quantity). Prints groups + rows."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=200,
            help="Max number of duplicate groups to print (default: 200).",
        )
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Also group by delivery_item_id (stricter duplicates).",
        )
        parser.add_argument(
            "--name-contains",
            type=str,
            default="",
            help="Optional filter: StockSupply.name contains (case-insensitive).",
        )
        parser.add_argument(
            "--date-from",
            type=str,
            default="",
            help="Optional filter: date >= YYYY-MM-DD",
        )
        parser.add_argument(
            "--date-to",
            type=str,
            default="",
            help="Optional filter: date <= YYYY-MM-DD",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        strict = options["strict"]
        name_contains = (options["name_contains"] or "").strip()
        date_from = (options["date_from"] or "").strip()
        date_to = (options["date_to"] or "").strip()

        group_fields = ["date", "name", "quantity"]
        if strict:
            group_fields.append("delivery_item_id")

        qs = StockSupply.objects.all()

        if name_contains:
            qs = qs.filter(name__icontains=name_contains)

        if date_from:
            qs = qs.filter(date__gte=date_from)

        if date_to:
            qs = qs.filter(date__lte=date_to)

        dupes = (
            qs.values(*group_fields)
            .annotate(cnt=Count("id"))
            .filter(cnt__gt=1)
            .order_by("-cnt", "date", "name")
        )

        total_groups = dupes.count()
        self.stdout.write(self.style.WARNING("=== STOCKSUPPLY DUPLICATE AUDIT ==="))
        self.stdout.write(f"Grouping fields: {group_fields}")
        self.stdout.write(f"Duplicate groups found: {total_groups}")

        if total_groups == 0:
            self.stdout.write(self.style.SUCCESS("No duplicates found."))
            self.stdout.write(self.style.WARNING("=== END ==="))
            return

        shown = 0
        for d in dupes[:limit]:
            shown += 1
            self.stdout.write("=" * 90)

            header_parts = []
            for f in group_fields:
                header_parts.append(f"{f}={d.get(f)}")
            header = " | ".join(header_parts) + f" | COUNT={d['cnt']}"

            self.stdout.write(header)

            filt = {f: d.get(f) for f in group_fields}
            rows = (
                StockSupply.objects.filter(**filt)
                .only("id", "delivery_item_id", "date", "name", "quantity", "value", "used")
                .order_by("id")
            )

            for s in rows:
                self.stdout.write(
                    f"  ID={s.id} delivery_item_id={s.delivery_item_id} "
                    f"value={s.value} used={s.used}"
                )

        self.stdout.write("=" * 90)
        self.stdout.write(f"Shown groups: {shown} / {total_groups} (limit={limit})")
        self.stdout.write(self.style.WARNING("=== END ==="))
