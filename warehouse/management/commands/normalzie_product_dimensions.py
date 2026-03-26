# warehouse/management/commands/normalize_product_dimensions.py
from django.core.management.base import BaseCommand
from django.db import transaction
from warehouse.models import Product
import re


class Command(BaseCommand):
    help = "Normalize product dimension separators to lowercase 'x'"

    def handle(self, *args, **options):
        qs = Product.objects.all()
        changed = 0

        with transaction.atomic():
            for p in qs:
                old = p.name
                new = re.sub(r"[xX]+", "x", old)

                if new != old:
                    # UWAGA: unique constraint
                    if not Product.objects.filter(name=new).exists():
                        p.name = new
                        p.save(update_fields=["name"])
                        changed += 1
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f"SKIP duplicate after normalize: {old}"
                            )
                        )

        self.stdout.write(self.style.SUCCESS(f"Done. Renamed: {changed}"))
