import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from warehouse.models import (
    Order, Delivery, DeliveryItem, DeliverySpecial, DeliverySpecialItem,
    WarehouseStock, StockSupply
)


class Command(BaseCommand):
    help = "Reset danych do wskazanej daty (domyślnie 2025-12-31): zakończ zamówienia, przetwórz dostawy, supply->used, wyzeruj stany."

    def add_arguments(self, parser):
        parser.add_argument("--cutoff", type=str, default="2025-12-31", help="YYYY-MM-DD")

    def handle(self, *args, **options):
        cutoff = datetime.date.fromisoformat(options["cutoff"])

        with transaction.atomic():
            orders_q = Q(order_date__lte=cutoff) | Q(order_date__isnull=True, customer_date__lte=cutoff)
            Order.objects.filter(orders_q).update(delivered=True, finished=True, updated=False)

            Delivery.objects.filter(date__lte=cutoff).update(processed=True, updated=False)
            DeliveryItem.objects.filter(delivery__date__lte=cutoff).update(processed=True, updated=False)

            DeliverySpecial.objects.filter(date__lte=cutoff).update(processed=True)
            DeliverySpecialItem.objects.filter(delivery__date__lte=cutoff).update(processed=True)

            supplies_q = Q(date__lte=cutoff) | Q(date__isnull=True, delivery_item__delivery__date__lte=cutoff)
            StockSupply.objects.filter(supplies_q).update(used=True)

            WarehouseStock.objects.update(quantity=0)

        self.stdout.write(self.style.SUCCESS(f"OK: reset wykonany do {cutoff}"))
