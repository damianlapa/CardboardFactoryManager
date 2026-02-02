from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from warehouse.models import Delivery, DeliveryItem, DeliveryPalette


class Command(BaseCommand):
    help = (
        "Cofa (usuwa) jedną dostawę Delivery po ID razem z jej elementami (DeliveryItem) "
        "oraz powiązaniami palet (DeliveryPalette). Domyślnie DRY-RUN."
    )

    def add_arguments(self, parser):
        parser.add_argument("--id", type=int, required=True, help="ID dostawy Delivery do usunięcia.")
        parser.add_argument("--apply", action="store_true", help="Wykonaj usuwanie (domyślnie DRY-RUN).")

    def handle(self, *args, **opts):
        delivery_id = opts["id"]
        apply = opts["apply"]

        try:
            d = Delivery.objects.get(id=delivery_id)
        except Delivery.DoesNotExist:
            raise CommandError(f"Delivery id={delivery_id} does not exist")

        items_qs = DeliveryItem.objects.filter(delivery=d)
        palettes_qs = DeliveryPalette.objects.filter(delivery=d)

        self.stdout.write("=== ROLLBACK DELIVERY ===")
        self.stdout.write(f"mode = {'APPLY' if apply else 'DRY-RUN'}")
        self.stdout.write(f"Delivery id={d.id} date={d.date} provider_id={getattr(d, 'provider_id', None)}")
        self.stdout.write("-" * 80)
        self.stdout.write(f"DeliveryItem to delete: {items_qs.count()}")
        self.stdout.write(f"DeliveryPalette to delete: {palettes_qs.count()}")
        self.stdout.write("Delivery to delete: 1")
        self.stdout.write("-" * 80)

        if not apply:
            self.stdout.write("DRY-RUN done. Add --apply to execute.")
            return

        with transaction.atomic():
            di = items_qs.delete()[0]
            dp = palettes_qs.delete()[0]
            dd = d.delete()[0]

        self.stdout.write("DELETED:")
        self.stdout.write(f"  DeliveryItem: {di}")
        self.stdout.write(f"  DeliveryPalette: {dp}")
        self.stdout.write(f"  Delivery: {dd}")
        self.stdout.write("DONE.")
