from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count, Sum

from warehouse.models import (
    WarehouseStock,
    WarehouseStockHistory,
    ProductSell3,
    OrderSettlement,
    ProductComplexParts,
)


class Command(BaseCommand):
    help = "Deduplicate WarehouseStock rows by (warehouse, stock): merge quantities and repoint FK refs."

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
            WarehouseStock.objects
            .values("warehouse_id", "stock_id")
            .annotate(c=Count("id"))
            .filter(c__gt=1)
            .order_by("-c", "warehouse_id", "stock_id")
        )

        total_groups = groups.count()
        if limit:
            groups = groups[:limit]

        if total_groups == 0:
            self.stdout.write(self.style.SUCCESS("No duplicate WarehouseStock groups found."))
            return

        self.stdout.write(self.style.WARNING(f"Found {total_groups} duplicate WarehouseStock groups."))

        merged_groups = 0
        deleted_ws = 0

        for g in groups:
            wh_id = g["warehouse_id"]
            stock_id = g["stock_id"]

            ws_list = list(
                WarehouseStock.objects
                .filter(warehouse_id=wh_id, stock_id=stock_id)
                .order_by("id")
            )

            keep = ws_list[0]
            others = ws_list[1:]

            total_qty = (
                WarehouseStock.objects
                .filter(warehouse_id=wh_id, stock_id=stock_id)
                .aggregate(s=Sum("quantity"))
                .get("s") or 0
            )

            # policz referencje do "others"
            others_ids = [w.id for w in others]
            hist_cnt = WarehouseStockHistory.objects.filter(warehouse_stock_id__in=others_ids).count()
            sell_cnt = ProductSell3.objects.filter(warehouse_stock_id__in=others_ids).count()
            settle_cnt = OrderSettlement.objects.filter(material_id__in=others_ids).count()
            parts_cnt = ProductComplexParts.objects.filter(part_id__in=others_ids).count()

            self.stdout.write(
                f"\nWS (warehouse_id={wh_id}, stock_id={stock_id})"
            )
            self.stdout.write(
                f"  KEEP:  id={keep.id} qty={keep.quantity}"
            )
            self.stdout.write(
                f"  MERGE: ids={others_ids} -> keep, total_qty={total_qty}"
            )
            self.stdout.write(
                f"  refs: History={hist_cnt}, Sell={sell_cnt}, OrderSettlement.material={settle_cnt}, ProductComplexParts.part={parts_cnt}"
            )

            if dry_run:
                continue

            # 1) ustaw keep.quantity = suma
            keep.quantity = int(total_qty)
            keep.save(update_fields=["quantity"])

            # 2) przepnij FK z "others" -> keep
            WarehouseStockHistory.objects.filter(warehouse_stock_id__in=others_ids).update(warehouse_stock=keep)
            ProductSell3.objects.filter(warehouse_stock_id__in=others_ids).update(warehouse_stock=keep)
            OrderSettlement.objects.filter(material_id__in=others_ids).update(material=keep)
            ProductComplexParts.objects.filter(part_id__in=others_ids).update(part=keep)

            # 3) usuń zbędne WS
            WarehouseStock.objects.filter(id__in=others_ids).delete()

            merged_groups += 1
            deleted_ws += len(others_ids)

        if dry_run:
            self.stdout.write(self.style.WARNING("\nDRY RUN complete. No changes were made."))
        else:
            self.stdout.write(self.style.SUCCESS(f"\nDone. merged_groups={merged_groups}, deleted_ws={deleted_ws}"))
