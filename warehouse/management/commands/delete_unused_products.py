from django.core.management.base import BaseCommand
from django.db.models import Exists, OuterRef
from warehouse.models import (
    Product,
    Order,
    ProductSell3,
    ProductComplexAssembly,
    BOM,
)


class Command(BaseCommand):
    help = "Usuwa produkty, które nigdzie nie są używane"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Tylko pokaż co zostanie usunięte (bez kasowania)",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        products = (
            Product.objects
            .annotate(
                used_in_orders=Exists(
                    Order.objects.filter(product=OuterRef("pk"))
                ),
                used_in_sales=Exists(
                    ProductSell3.objects.filter(product=OuterRef("pk"))
                ),
                used_in_assemblies=Exists(
                    ProductComplexAssembly.objects.filter(product=OuterRef("pk"))
                ),
                used_in_boms=Exists(
                    BOM.objects.filter(product=OuterRef("pk"))
                ),
            )
            .filter(
                used_in_orders=False,
                used_in_sales=False,
                used_in_assemblies=False,
                used_in_boms=False,
            )
        )

        count = products.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS("Brak nieużywanych produktów 🎉"))
            return

        self.stdout.write(
            self.style.WARNING(f"Znaleziono {count} nieużywanych produktów:")
        )

        for p in products.order_by("name"):
            self.stdout.write(f" - [{p.id}] {p.name}")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY-RUN: nic nie zostało usunięte"))
            return

        deleted, _ = products.delete()

        self.stdout.write(
            self.style.SUCCESS(f"Usunięto {deleted} rekordów (Product)")
        )
