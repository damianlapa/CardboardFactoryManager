from __future__ import annotations

import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import F


class Command(BaseCommand):
    help = (
        "Rollback Deliveries from a given date (default 2026-01-01):\n"
        "- for each DeliveryItem: finds StockSupply rows (delivery_item FK)\n"
        "- deletes WarehouseStockHistory rows linked to stock_supply\n"
        "- decreases WarehouseStock.quantity by delivered quantity\n"
        "- deletes StockSupplySettlement rows for those supplies\n"
        "- deletes empty OrderSettlement created for delivery (if no more StockSupplySettlement)\n"
        "- deletes StockSupply rows\n"
        "- sets DeliveryItem.processed=False\n"
        "- updates Order.delivered_quantity and sets Order.delivered=False (forced)\n"
        "- sets Delivery.processed=False\n"
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
        parser.add_argument(
            "--audit",
            action="store_true",
            help="Print additional info (items / supplies / history counts).",
        )

    def handle(self, *args, **options):
        from_date = self._parse_date(options["from_date"])
        commit = bool(options["commit"])
        limit = options["limit"]
        audit = bool(options["audit"])
        dry_run = not commit

        # --- import models here ---
        from warehouse.models import (
            Delivery,
            DeliveryItem,
            StockSupply,
            StockSupplySettlement,
            OrderSettlement,
            WarehouseStock,
            WarehouseStockHistory,
            Order,
        )

        deliveries_qs = (
            Delivery.objects
            .filter(date__gte=from_date)
            .select_related("provider")
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
                        audit=audit,
                        DeliveryItem=DeliveryItem,
                        StockSupply=StockSupply,
                        StockSupplySettlement=StockSupplySettlement,
                        OrderSettlement=OrderSettlement,
                        WarehouseStock=WarehouseStock,
                        WarehouseStockHistory=WarehouseStockHistory,
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
        audit: bool,
        DeliveryItem,
        StockSupply,
        StockSupplySettlement,
        OrderSettlement,
        WarehouseStock,
        WarehouseStockHistory,
        Order,
    ):
        provider_label = getattr(delivery.provider, "name", None) or str(delivery.provider_id)
        self.stdout.write(
            f"DELIVERY #{delivery.id} | date={delivery.date} | provider={provider_label} | car={delivery.car_number or '-'}"
        )

        items = (
            DeliveryItem.objects
            .filter(delivery_id=delivery.id)
            .select_related("order", "stock")
            .order_by("id")
        )

        self.stdout.write(f"  Items: {items.count()}")

        # keep track of settlements we might remove (after deleting StockSupplySettlement)
        touched_settlement_ids: set[int] = set()

        for item in items:
            self.stdout.write(f"  - ITEM #{item.id} | order_id={item.order_id} | stock_id={item.stock_id} | qty={item.quantity} | processed={item.processed}")

            # StockSupply created in add_to_warehouse() has FK delivery_item=self
            supplies_qs = StockSupply.objects.filter(delivery_item_id=item.id).select_related("warehouse_stock", "order")

            supplies_count = supplies_qs.count()
            if dry_run:
                self.stdout.write(f"    StockSupply rows: {supplies_count}")
            else:
                self.stdout.write(f"    StockSupply rows: {supplies_count}")

            # If there are multiple (shouldn't, but be safe), rollback all
            for ss in supplies_qs:
                qty = ss.quantity

                # Lock WarehouseStock row
                ws = WarehouseStock.objects.select_for_update().get(pk=ss.warehouse_stock_id)

                ws_before = ws.quantity
                ws_after = ws_before - qty

                # History linked to this stock_supply
                hist_qs = WarehouseStockHistory.objects.filter(stock_supply_id=ss.id)
                hist_count = hist_qs.count()

                # Settlements linked to this stock_supply
                ssett_qs = StockSupplySettlement.objects.filter(stock_supply_id=ss.id).select_related("settlement")
                ssett_count = ssett_qs.count()
                if ssett_count:
                    touched_settlement_ids.update(ssett_qs.values_list("settlement_id", flat=True))

                if dry_run:
                    self.stdout.write(f"    StockSupply #{ss.id} | ws_id={ws.id} | ws.qty: {ws_before} -> {ws_after}")
                    self.stdout.write(f"      History to delete: {hist_count}")
                    self.stdout.write(f"      StockSupplySettlement to delete: {ssett_count}")
                else:
                    # delete history
                    deleted_hist, _ = hist_qs.delete()
                    # delete settlement rows
                    deleted_ssett, _ = ssett_qs.delete()

                    # decrease warehouse stock
                    ws.quantity = ws_after if ws_after >= 0 else 0
                    ws.save(update_fields=["quantity"])

                    # delete stock supply
                    ss.delete()

                    self.stdout.write(f"    StockSupply #{ss.id} | ws_id={ws.id} | ws.qty: {ws_before} -> {ws.quantity}")
                    self.stdout.write(f"      Deleted history rows: {deleted_hist}")
                    self.stdout.write(f"      Deleted StockSupplySettlement rows: {deleted_ssett}")
                    if ws_after < 0:
                        self.stdout.write("      WARNING: ws_after < 0, clamped to 0 (data mismatch).")

                # Update Order delivered_quantity and delivered flag (forced false)
                # Use item's order (same as ss.order) to avoid weirdness.
                order = item.order
                if order_id := getattr(order, "id", None):
                    if dry_run:
                        new_delivered_qty = max(int(order.delivered_quantity) - int(qty), 0)
                        self.stdout.write(
                            f"      Order #{order_id}: delivered_quantity {order.delivered_quantity} -> {new_delivered_qty}, delivered=False"
                        )
                    else:
                        # lock order to avoid race
                        order_locked = Order.objects.select_for_update().get(pk=order_id)
                        new_delivered_qty = max(int(order_locked.delivered_quantity) - int(qty), 0)
                        order_locked.delivered_quantity = new_delivered_qty
                        order_locked.delivered = False  # forced (as requested)
                        if new_delivered_qty == 0:
                            order_locked.delivery_date = None
                        order_locked.save(update_fields=["delivered_quantity", "delivered", "delivery_date"])
                        self.stdout.write(
                            f"      Order #{order_id}: delivered_quantity {order.delivered_quantity} -> {new_delivered_qty}, delivered=False"
                        )

            # Mark item as not processed
            if dry_run:
                self.stdout.write("    Would set DeliveryItem.processed=False")
            else:
                if item.processed:
                    item.processed = False
                    item.save(update_fields=["processed"])
                self.stdout.write("    Set DeliveryItem.processed=False")

        # Clean up potentially empty settlements created by deliveries
        # We only delete settlements that now have no StockSupplySettlement rows left.
        if touched_settlement_ids:
            if audit:
                self.stdout.write(f"  Settlements touched: {sorted(touched_settlement_ids)}")

            for sid in sorted(touched_settlement_ids):
                # if anything still references it, skip
                still_has = StockSupplySettlement.objects.filter(settlement_id=sid).exists()
                if dry_run:
                    self.stdout.write(f"  OrderSettlement #{sid}: would delete if empty (still_has_stocksupplysettlement={still_has})")
                else:
                    if not still_has:
                        OrderSettlement.objects.filter(pk=sid).delete()
                        self.stdout.write(f"  Deleted empty OrderSettlement #{sid}")
                    else:
                        self.stdout.write(f"  Kept OrderSettlement #{sid} (still has StockSupplySettlement)")

        # Finally mark delivery as not processed
        if dry_run:
            self.stdout.write("  Would set Delivery.processed=False")
        else:
            if delivery.processed:
                delivery.processed = False
                delivery.save(update_fields=["processed"])
            self.stdout.write("  Set Delivery.processed=False")

    def _parse_date(self, s: str) -> datetime.date:
        try:
            y, m, d = map(int, s.split("-"))
            return datetime.date(y, m, d)
        except Exception:
            raise ValueError(f"Invalid date: {s}. Expected YYYY-MM-DD.")


class _DryRunRollback(Exception):
    """Internal exception to force transaction rollback in dry-run mode."""
    pass
