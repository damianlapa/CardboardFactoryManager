from django.core.management.base import BaseCommand
from warehouse.models import WarehouseStock, WarehouseStockHistory


class Command(BaseCommand):
    help = "Audit WarehouseStock which did not start from quantity 0"

    def handle(self, *args, **options):
        self.stdout.write("\n=== AUDIT: WAREHOUSE STOCK START STATE ===\n")

        total_ws = WarehouseStock.objects.count()
        self.stdout.write(f"Total WarehouseStock: {total_ws}")

        problematic = []
        checked = 0

        for ws in WarehouseStock.objects.select_related("stock", "warehouse"):
            checked += 1

            first_record = (
                WarehouseStockHistory.objects
                .filter(warehouse_stock=ws)
                .order_by("date", "id")
                .first()
            )

            if not first_record:
                continue

            if first_record.quantity_before != 0:
                problematic.append((ws, first_record))

        self.stdout.write(f"\nChecked: {checked}")
        self.stdout.write(f"Problematic (started != 0): {len(problematic)}\n")

        if problematic:
            self.stdout.write("---- DETAILS ----\n")

            for ws, record in problematic:
                self.stdout.write(
                    f"WS_ID={ws.id} | "
                    f"Warehouse={ws.warehouse.name} | "
                    f"Stock={ws.stock.name} | "
                    f"FirstDate={record.date} | "
                    f"Before={record.quantity_before} | "
                    f"After={record.quantity_after}"
                )

        self.stdout.write("\n=== END ===\n")