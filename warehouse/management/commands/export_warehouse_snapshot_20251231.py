import csv
import datetime
from django.core.management.base import BaseCommand

from warehouse.models import WarehouseStock

SNAPSHOT_DATE = datetime.date(2025, 12, 31)


class Command(BaseCommand):
    help = (
        "Eksportuje aktualne stany magazynowe (WarehouseStock.quantity > 0) "
        "jako snapshot na dzień 2025-12-31. "
        "Nie modyfikuje danych."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--out",
            type=str,
            default="warehouse_snapshot_2025-12-31.csv",
            help="Ścieżka do pliku CSV (domyślnie: warehouse_snapshot_2025-12-31.csv)",
        )
        parser.add_argument(
            "--include-zero",
            action="store_true",
            help="Uwzględnij także WarehouseStock z quantity=0 (domyślnie pomijane).",
        )

    def handle(self, *args, **opts):
        out_path = opts["out"]
        include_zero = opts["include_zero"]

        qs = WarehouseStock.objects.select_related(
            "warehouse",
            "stock",
            "stock__stock_type",
        )

        if not include_zero:
            qs = qs.filter(quantity__gt=0)

        count = qs.count()

        self.stdout.write("=== EXPORT WAREHOUSE SNAPSHOT ===")
        self.stdout.write(f"snapshot_date = {SNAPSHOT_DATE}")
        self.stdout.write(f"rows = {count}")
        self.stdout.write(f"output = {out_path}")
        self.stdout.write("-" * 80)

        if count == 0:
            self.stdout.write("No rows to export.")
            return

        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=";")

            # nagłówki
            writer.writerow([
                "snapshot_date",
                "warehouse_id",
                "warehouse_name",
                "stock_id",
                "stock_name",
                "stock_type",
                "quantity",
            ])

            for ws in qs.order_by("warehouse__id", "stock__name"):
                writer.writerow([
                    SNAPSHOT_DATE.isoformat(),
                    ws.warehouse_id,
                    ws.warehouse.name,
                    ws.stock_id,
                    ws.stock.name,
                    ws.stock.stock_type.name if ws.stock.stock_type else "",
                    ws.quantity,
                ])

        self.stdout.write("DONE.")
