from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from warehouse.models import DeliverySpecial, DeliverySpecialItem


class Command(BaseCommand):
    help = "Cofa (usuwa) jedną dostawę DeliverySpecial po ID razem z jej elementami. Domyślnie DRY-RUN."

    def add_arguments(self, parser):
        parser.add_argument("--id", type=int, required=True, help="ID dostawy DeliverySpecial do usunięcia.")
        parser.add_argument("--apply", action="store_true", help="Wykonaj usuwanie (domyślnie DRY-RUN).")

    def handle(self, *args, **opts):
        delivery_id = opts["id"]
        apply = opts["apply"]

        try:
            d = DeliverySpecial.objects.get(id=delivery_id)
        except DeliverySpecial.DoesNotExist:
            raise CommandError(f"DeliverySpecial id={delivery_id} does not exist")

        items_qs = DeliverySpecialItem.objects.filter(delivery=d)

        self.stdout.write("=== ROLLBACK DELIVERY SPECIAL ===")
        self.stdout.write(f"mode = {'APPLY' if apply else 'DRY-RUN'}")
        self.stdout.write(f"DeliverySpecial id={d.id} date={d.date}")
        self.stdout.write("-" * 80)
        self.stdout.write(f"DeliverySpecialItem to delete: {items_qs.count()}")
        self.stdout.write("DeliverySpecial to delete: 1")
        self.stdout.write("-" * 80)

        if not apply:
            self.stdout.write("DRY-RUN done. Add --apply to execute.")
            return

        with transaction.atomic():
            di = items_qs.delete()[0]
            dd = d.delete()[0]

        self.stdout.write("DELETED:")
        self.stdout.write(f"  DeliverySpecialItem: {di}")
        self.stdout.write(f"  DeliverySpecial: {dd}")
        self.stdout.write("DONE.")
