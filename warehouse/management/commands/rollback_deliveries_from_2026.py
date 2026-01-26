from __future__ import annotations

import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Max


class Command(BaseCommand):
    help = (
        "Rollback Deliveries from a given date (default 2026-01-01):\n"
        "- for Delivery(date>=from_date) iterates DeliveryItem\n"
        "- deletes WarehouseStockHistory rows linked by StockSupply\n"
        "- deletes StockSupply (+ defensive cleanup of settlements/sells if any)\n"
        "- restores WarehouseStock.quantity (subtracts stock_supply.quantity)\n"
        "- updates Order.delivered_quantity / delivered / delivery_date\n"
        "- deletes DeliveryItem and Delivery (if empty)\n"
        "Default is DRY RUN. Use --commit to apply."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--from-date",
            type=str,
            default="2026-01-01",
            help="Rollback deliveries with date >= FROM_DATE (YYYY-MM-DD). Default: 2026-01-01",
        )
        parser.add_argument(
            "--commit",
            action="store_true",
            help="Apply changes. Without this flag it runs in dry-run mode.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Limit number of deliveries processed (newest first). Useful for testing.",
        )

    def handle(self, *args, **options):
        from_date = self._parse_date(options["from_date"])
        commit = bool(options["commit"])
        limit = options["limit"]
        dry_run = not commit

        # --- Import models here to avoid app loading issues ---
        from warehouse.models import (
            Delivery,
            DeliveryItem,
            StockSupply,
            WarehouseStock,
            WarehouseStockHistory,
            StockSupplySettlement,
            StockSupplySell,
            Order,
        )

        deliveries_qs = (
            Delivery.objects
            .filter(date__gte=from_date)
            .order_by("-date", "-id")
        )
        if limit:
            deliveries_qs = deliveries_qs[:limit]

        total = deliveries_qs.count()

        self.stdout.write("")
        self.stdout.write("=== ROLLBACK DELIVERIES ===")
        self.stdout.write(f"FROM DATE: {from_date.isoformat()}")
        self.stdout.write(f"TOTAL DELIVERIES: {total}")
        self.stdout.write(f"MODE: {'COMMIT' if commit else 'DRY RUN'}")
        self.stdout.write("")

        if total == 0:
            self.stdout.write("Nothing to do.")
            return

        try:
            with transaction.atomic():
                for delivery in deliveries_qs:
                    self.stdout.write("=" * 110)
                    self._process_one_delivery(
                        delivery=delivery,
                        dry_run=dry_run,
                        DeliveryItem=DeliveryItem,
                        StockSupply=StockSupply,
                        WarehouseStock=WarehouseStock,
                        WarehouseStockHistory=WarehouseStockHistory,
                        StockSupplySettlement=StockSupplySettlement,
                        StockSupplySell=StockSupplySell,
                        Order=Order,
                    )

                self.stdout.write("=" * 110)
                self.stdout.write("DONE.")
                self.stdout.write("")

                if dry_run:
                    raise _DryRunRollback()

        except _DryRunRollback:
            self.stdout.write("DRY RUN: no changes were saved (transaction rolled back).")
            self.stdout.write("")

    def _process_one_delivery(
        self,
        *,
        delivery,
        dry_run: bool,
        DeliveryItem,
        StockSupply,
        WarehouseStock,
        WarehouseStockHistory,
        StockSupplySettlement,
        StockSupplySell,
        Order,
    ):
        self.stdout.write(f"DELIVERY #{delivery.id} | date={delivery.date} | name={delivery.name}")

        items = (
            DeliveryItem.objects
            .filter(delivery_id=delivery.id)
            .select_related("order", "stock")
            .order_by("id")
        )

        self.stdout.write(f"  DeliveryItems: {items.count()}")

        # Track orders touched to recompute delivery_date properly
        touched_order_ids: set[int] = set()

        for item in items:
            touched_order_ids.add(item.order_id)

            self.stdout.write(
                f"  - ITEM #{item.id} | order_id={item.order_id} | stock_id={item.stock_id} | qty={item.quantity} | processed={item.processed}"
            )

            supplies = (
                StockSupply.objects
                .filter(delivery_item_id=item.id)
                .select_related("warehouse_stock")
                .order_by("id")
            )

            self.stdout.write(f"    StockSupply rows: {supplies.count()}")

            for ss in supplies:
                # lock WarehouseStock
                ws = WarehouseStock.objects.select_for_update().get(pk=ss.warehouse_stock_id)

                qty_before = ws.quantity
                qty_after = qty_before - ss.quantity

                if qty_after < 0:
                    # Nie blokuję rollbacku, ale to jest sygnał, że były kolejne ruchy
                    self.stdout.write(
                        f"    WARNING: WarehouseStock would go negative! ws_id={ws.id} {qty_before} - {ss.quantity} = {qty_after}"
                    )

                # history linked by stock_supply (PROTECT => must delete history first)
                hist_qs = WarehouseStockHistory.objects.filter(stock_supply_id=ss.id)
                hist_count = hist_qs.count()

                # defensive cleanup (should be empty if 2026 had no BOM/settlements/sells)
                ssett_qs = StockSupplySettlement.objects.filter(stock_supply_id=ss.id)
                ssett_count = ssett_qs.count()

                ssell_qs = StockSupplySell.objects.filter(stock_supply_id=ss.id)
                ssell_count = ssell_qs.count()

                if dry_run:
                    self.stdout.write(f"    StockSupply #{ss.id} | qty={ss.quantity} | value={ss.value} | ws_id={ws.id}")
                    self.stdout.write(f"      History to delete: {hist_count}")
                    self.stdout.write(f"      StockSupplySettlement to delete: {ssett_count}")
                    self.stdout.write(f"      StockSupplySell to delete: {ssell_count}")
                    self.stdout.write(f"      WarehouseStock.quantity: {qty_before} -> {qty_after}")
                    self.stdout.write(f"      Would delete StockSupply.")
                else:
                    deleted_hist, _ = hist_qs.delete()
                    deleted_ssett, _ = ssett_qs.delete()
                    deleted_ssell, _ = ssell_qs.delete()

                    ws.quantity = qty_after
                    ws.save(update_fields=["quantity"])

                    # delete supply (now safe)
                    ss.delete()

                    self.stdout.write(f"    StockSupply #{ss.id} rolled back.")
                    self.stdout.write(f"      Deleted history: {deleted_hist}")
                    self.stdout.write(f"      Deleted supply settlements: {deleted_ssett}")
                    self.stdout.write(f"      Deleted supply sells: {deleted_ssell}")
                    self.stdout.write(f"      Updated WarehouseStock.quantity: {qty_before} -> {qty_after}")

            # Update order delivered_quantity etc (based on item.quantity)
            if dry_run:
                self.stdout.write(f"    Would update Order #{item.order_id}: delivered_quantity -= {item.quantity}")
                self.stdout.write(f"    Would delete DeliveryItem #{item.id}")
            else:
                order = item.order
                order.delivered_quantity = max(0, (order.delivered_quantity or 0) - item.quantity)

                # delivered flag
                order.delivered = bool(order.delivered_quantity >= (order.order_quantity or 0))

                order.save(update_fields=["delivered_quantity", "delivered"])

                # delete item
                item.delete()

        # Recompute delivery_date for touched orders (max date among remaining processed items)
        if touched_order_ids:
            for oid in sorted(touched_order_ids):
                if dry_run:
                    self.stdout.write(f"  Would recompute Order #{oid}.delivery_date from remaining processed DeliveryItems.")
                else:
                    max_date = (
                        DeliveryItem.objects
                        .filter(order_id=oid, processed=True)
                        .aggregate(mx=Max("delivery__date"))
                        .get("mx")
                    )
                    Order.objects.filter(id=oid).update(delivery_date=max_date)

        # delete delivery if now empty
        remaining = DeliveryItem.objects.filter(delivery_id=delivery.id).count()
        if dry_run:
            self.stdout.write(f"  DeliveryItems remaining after rollback: {remaining}")
            if remaining == 0:
                self.stdout.write("  Would delete Delivery.")
        else:
            if remaining == 0:
                delivery.delete()
                self.stdout.write("  Deleted Delivery (no items left).")
            else:
                self.stdout.write(f"  Delivery kept (still has {remaining} items).")

    def _parse_date(self, s: str) -> datetime.date:
        try:
            y, m, d = map(int, s.split("-"))
            return datetime.date(y, m, d)
        except Exception:
            raise ValueError(f"Invalid date: {s}. Expected YYYY-MM-DD.")


class _DryRunRollback(Exception):
    """Internal exception to force transaction rollback in dry-run mode."""
    pass
