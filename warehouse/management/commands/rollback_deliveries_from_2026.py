from __future__ import annotations

import datetime
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import F


class Command(BaseCommand):
    help = (
        "Rollback Deliveries from a given date (default 2026-01-01):\n"
        "- for each DeliveryItem: deletes StockSupply + WarehouseStockHistory linked to it\n"
        "- restores WarehouseStock.quantity (subtracts item.quantity)\n"
        "- updates Order.delivered_quantity (subtracts item.quantity) and recomputes delivered flag\n"
        "- deletes DeliveryPalette rows (PROTECT)\n"
        "- deletes DeliveryItem, then Delivery\n"
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
            "--warehouse-name",
            type=str,
            default="MAGAZYN GŁÓWNY",
            help="Warehouse name used for DeliveryItem.add_to_warehouse(). Default: MAGAZYN GŁÓWNY",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Limit number of deliveries processed (newest first). Useful for testing.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force rollback even if StockSupply has settlements/sells linked (NOT recommended).",
        )
        parser.add_argument(
            "--audit",
            action="store_true",
            help="Print extra diagnostics per item (stock/warehouse_stock ids etc.).",
        )

    def handle(self, *args, **options):
        from_date = self._parse_date(options["from_date"])
        commit = bool(options["commit"])
        warehouse_name = options["warehouse_name"]
        limit = options["limit"]
        force = bool(options["force"])
        audit = bool(options["audit"])

        # --- Import models here ---
        from warehouse.models import (
            Delivery,
            DeliveryItem,
            DeliveryPalette,
            StockSupply,
            StockSupplySell,
            StockSupplySettlement,
            Warehouse,
            WarehouseStock,
            WarehouseStockHistory,
            Stock,
            StockType,
            Order,
        )

        dry_run = not commit

        try:
            warehouse = Warehouse.objects.get(name=warehouse_name)
        except Warehouse.DoesNotExist:
            raise CommandError(f"Warehouse '{warehouse_name}' not found.")

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
        self.stdout.write(f"WAREHOUSE: {warehouse_name}")
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
                        force=force,
                        audit=audit,
                        warehouse=warehouse,
                        DeliveryItem=DeliveryItem,
                        DeliveryPalette=DeliveryPalette,
                        StockSupply=StockSupply,
                        StockSupplySell=StockSupplySell,
                        StockSupplySettlement=StockSupplySettlement,
                        WarehouseStock=WarehouseStock,
                        WarehouseStockHistory=WarehouseStockHistory,
                        Stock=Stock,
                        StockType=StockType,
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
        force: bool,
        audit: bool,
        warehouse,
        DeliveryItem,
        DeliveryPalette,
        StockSupply,
        StockSupplySell,
        StockSupplySettlement,
        WarehouseStock,
        WarehouseStockHistory,
        Stock,
        StockType,
        Order,
    ):
        provider_str = getattr(delivery.provider, "name", str(delivery.provider_id))
        car_str = getattr(delivery, "car_number", None) or getattr(delivery, "car", None) or ""
        self.stdout.write(f"DELIVERY #{delivery.id} | date={delivery.date} | provider={provider_str} | car={car_str}")

        items = (
            DeliveryItem.objects
            .filter(delivery_id=delivery.id)
            .select_related("order")
            .order_by("id")
        )
        self.stdout.write(f"  Items: {items.count()}")

        # Rollback each item
        for item in items:
            self._process_one_item(
                item=item,
                delivery_date=delivery.date,
                dry_run=dry_run,
                force=force,
                audit=audit,
                warehouse=warehouse,
                StockSupply=StockSupply,
                StockSupplySell=StockSupplySell,
                StockSupplySettlement=StockSupplySettlement,
                WarehouseStock=WarehouseStock,
                WarehouseStockHistory=WarehouseStockHistory,
                Stock=Stock,
                StockType=StockType,
                Order=Order,
            )

            # delete DeliveryItem itself (we are removing the whole delivery event)
            if dry_run:
                self.stdout.write(f"    Would delete DeliveryItem id={item.id}.")
            else:
                item.delete()
                self.stdout.write(f"    Deleted DeliveryItem id={item.id}.")

        # DeliveryPalette is PROTECT -> must delete first
        palettes_qs = DeliveryPalette.objects.filter(delivery_id=delivery.id)
        if dry_run:
            self.stdout.write(f"  DeliveryPalette rows to delete: {palettes_qs.count()}")
            self.stdout.write("  Would delete Delivery.")
        else:
            dp_deleted, _ = palettes_qs.delete()
            self.stdout.write(f"  Deleted DeliveryPalette rows: {dp_deleted}")
            delivery.delete()
            self.stdout.write("  Deleted Delivery.")

    def _process_one_item(
        self,
        *,
        item,
        delivery_date,
        dry_run: bool,
        force: bool,
        audit: bool,
        warehouse,
        StockSupply,
        StockSupplySell,
        StockSupplySettlement,
        WarehouseStock,
        WarehouseStockHistory,
        Stock,
        StockType,
        Order,
    ):
        order = item.order

        self.stdout.write(
            f"    ITEM #{item.id} | order_id={order.id} | qty={item.quantity} | "
            f"name='{order.name}' | dims='{order.dimensions}'"
        )

        # Find StockSupply created from this DeliveryItem (if processed in the past)
        ss_qs = StockSupply.objects.filter(delivery_item_id=item.id)
        ss_count = ss_qs.count()

        if dry_run:
            self.stdout.write(f"      StockSupply linked to item: {ss_count}")
        # In commit mode we will actually delete them, but first: guard if used somewhere else
        for ss in ss_qs:
            used_sells = StockSupplySell.objects.filter(stock_supply_id=ss.id).count()
            used_settlements = StockSupplySettlement.objects.filter(stock_supply_id=ss.id).count()
            if (used_sells or used_settlements) and not force:
                raise CommandError(
                    f"StockSupply id={ss.id} for DeliveryItem id={item.id} "
                    f"has links: sells={used_sells}, settlements={used_settlements}. "
                    f"Run sells/settlements rollback first, or use --force (risky)."
                )

            hist_qs = WarehouseStockHistory.objects.filter(stock_supply_id=ss.id)
            if dry_run:
                self.stdout.write(f"      WarehouseStockHistory to delete (by stock_supply): {hist_qs.count()}")
            else:
                hist_deleted, _ = hist_qs.delete()
                self.stdout.write(f"      Deleted WarehouseStockHistory rows: {hist_deleted}")

            if dry_run:
                self.stdout.write(f"      Would delete StockSupply id={ss.id}.")
            else:
                ss.delete()
                self.stdout.write(f"      Deleted StockSupply id={ss.id}.")

        # Restore WarehouseStock.quantity (reverse add_to_warehouse)
        stock_type = StockType.objects.get(stock_type="material", unit="PIECE")
        stock_name = f"{order.name}[{order.dimensions}]"
        stock, _ = Stock.objects.get_or_create(name=stock_name, stock_type=stock_type)

        # Lock warehouse_stock row
        ws = WarehouseStock.objects.select_for_update().get(warehouse=warehouse, stock=stock)

        qty_before = ws.quantity
        qty_after = qty_before - item.quantity
        if qty_after < 0:
            # We do NOT silently clamp in commit mode (this indicates data mismatch)
            msg = (
                f"WarehouseStock id={ws.id} would go negative: {qty_before} - {item.quantity} = {qty_after} "
                f"(order_id={order.id}, delivery_item_id={item.id})."
            )
            raise CommandError(msg)

        if dry_run:
            self.stdout.write(f"      WarehouseStock.quantity: {qty_before} -> {qty_after}")
        else:
            ws.quantity = qty_after
            ws.save(update_fields=["quantity"])
            self.stdout.write(f"      Updated WarehouseStock.quantity: {qty_before} -> {qty_after}")

        if audit:
            self.stdout.write(f"      AUDIT: warehouse_stock_id={ws.id} stock_id={stock.id}")

        # Update Order.delivered_quantity and recompute delivered flag
        # Lock order row too
        order_locked = Order.objects.select_for_update().get(pk=order.id)

        dq_before = order_locked.delivered_quantity or 0
        dq_after = dq_before - item.quantity
        if dq_after < 0:
            dq_after = 0  # safe clamp; delivered_quantity should never be negative

        # recompute delivered based on ratio > 0.92 (same as your add_to_warehouse)
        delivered_new = False
        if order_locked.order_quantity:
            delivered_new = (dq_after / order_locked.order_quantity) > 0.92

        if dry_run:
            self.stdout.write(
                f"      Order.delivered_quantity: {dq_before} -> {dq_after} | "
                f"delivered: {order_locked.delivered} -> {delivered_new}"
            )
        else:
            order_locked.delivered_quantity = dq_after
            order_locked.delivered = delivered_new
            if delivered_new:
                # keep delivery_date as-is OR set to delivery_date if missing
                if not order_locked.delivery_date:
                    order_locked.delivery_date = delivery_date
            else:
                # if we just revoked "delivered", clear delivery_date
                order_locked.delivery_date = None

            order_locked.save(update_fields=["delivered_quantity", "delivered", "delivery_date"])
            self.stdout.write(
                f"      Updated Order: delivered_quantity {dq_before}->{dq_after}, "
                f"delivered {order_locked.delivered}"
            )

    def _parse_date(self, s: str) -> datetime.date:
        try:
            y, m, d = map(int, s.split("-"))
            return datetime.date(y, m, d)
        except Exception:
            raise CommandError(f"Invalid date: {s}. Expected YYYY-MM-DD.")


class _DryRunRollback(Exception):
    """Internal exception to force transaction rollback in dry-run mode."""
    pass
