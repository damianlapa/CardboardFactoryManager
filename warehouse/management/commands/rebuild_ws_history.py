from django.core.management.base import BaseCommand
from django.db import transaction

from warehouse.models import WarehouseStock
from warehouse.services.stock_moves import rebuild_ws_history_from_date


class Command(BaseCommand):
    help = "Przelicza WS history dla wszystkich WarehouseStock na podstawie delta."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=None)
        parser.add_argument("--ws-id", type=int, default=None, help="Tylko jeden WarehouseStock id")

    def handle(self, *args, **opts):
        limit = opts["limit"]
        ws_id = opts["ws_id"]

        qs = WarehouseStock.objects.all().order_by("id")
        if ws_id:
            qs = qs.filter(id=ws_id)

        if limit:
            qs = qs[:limit]

        total = qs.count()
        self.stdout.write(f"=== REBUILD WS HISTORY (delta-based) ===")
        self.stdout.write(f"WS count: {total}")

        i = 0
        for ws in qs.iterator():
            i += 1
            with transaction.atomic():
                rebuild_ws_history_from_date(ws=ws, from_date=None)
            if i % 50 == 0:
                self.stdout.write(f"  rebuilt {i}/{total}")

        self.stdout.write("=== DONE ===")
