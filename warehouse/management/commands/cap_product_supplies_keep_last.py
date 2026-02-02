from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

from warehouse.models import (
    StockSupply,
    StockSupplySell,
    StockSupplySettlement,
    ProductSell3,
    WarehouseStock,
    WarehouseStockHistory,
    Stock,
)


class Command(BaseCommand):
    help = (
        "Cap availability for PRODUCT supplies (usually as_result=True). "
        "Consumes OLD supplies so that only last KEEP pcs remain available. "
        "Default is DRY-RUN; use --apply to write changes."
    )

    def add_arguments(self, parser):
        parser.add_argument("--name", required=True, help="Exact StockSupply.name (normalized string).")
        parser.add_argument("--keep", type=int, required=True, help="How many pcs should remain available in total.")
        parser.add_argument("--date", default=None, help="Date for adjustment sell (YYYY-MM-DD). Default: today.")
        parser.add_argument("--warehouse-stock-id", type=int, default=None,
                            help="WarehouseStock id to reconcile quantity/history. If omitted, tries to auto-detect.")
        parser.add_argument("--apply", action="store_true", help="Apply changes (default dry-run).")
        parser.add_argument("--no-reconcile-ws", action="store_true",
                            help="Do NOT change WarehouseStock.quantity (only consume supplies).")

    def handle(self, *args, **opts):
        name = opts["name"]
        keep = int(opts["keep"])
        apply = bool(opts["apply"])
        ws_id = opts["warehouse_stock_id"]
        no_reconcile = bool(opts["no_reconcile_ws"])

        if keep < 0:
            raise ValidationError("--keep must be >= 0")

        if opts["date"]:
            y, m, d = map(int, opts["date"].split("-"))
            adj_date = timezone.datetime(y, m, d).date()
        else:
            adj_date = timezone.now().date()

        # 1) find supplies for this name (PRODUCT) and preferably as_result=True
        qs = (
            StockSupply.objects
            .filter(name=name, stock_type__stock_type="product")
            .filter(stocksupplysettlement__as_result=True)
            .distinct()
            .order_by("date", "id")
        )
        supplies = list(qs)

        if not supplies:
            self.stdout.write(self.style.WARNING(
                f"No supplies found with as_result=True for name={name!r}. Fallback to all product supplies by name."
            ))
            supplies = list(
                StockSupply.objects
                .filter(name=name, stock_type__stock_type="product")
                .order_by("date", "id")
            )

        if not supplies:
            raise ValidationError(f"No product StockSupply found for name={name!r}")

        # Lock safety: we will lock rows only in APPLY mode
        # (dry-run uses read only)

        def supply_info(s):
            return {
                "id": s.id,
                "date": str(s.date),
                "qty": int(s.quantity),
                "avail": int(s.available_quantity()),
                "used": bool(s.used),
                "value": str(s.value),
            }

        # Current availability
        current_avails = [int(s.available_quantity()) for s in supplies]
        total_available = sum(current_avails)

        self.stdout.write("=== CAP PRODUCT SUPPLIES ===")
        self.stdout.write(f"name = {name}")
        self.stdout.write(f"keep = {keep}")
        self.stdout.write(f"supplies_count = {len(supplies)}")
        self.stdout.write(f"total_available_now = {total_available}")
        self.stdout.write("First 10 supplies (oldest->newest):")
        for s in supplies[:10]:
            self.stdout.write(f"  {supply_info(s)}")
        self.stdout.write("Last 10 supplies (oldest->newest):")
        for s in supplies[-10:]:
            self.stdout.write(f"  {supply_info(s)}")

        if total_available <= keep:
            self.stdout.write(self.style.SUCCESS(
                f"Nothing to do: total_available ({total_available}) <= keep ({keep})."
            ))
            return

        excess = total_available - keep
        self.stdout.write(self.style.WARNING(f"Need to consume EXCESS = {excess} pcs from OLDEST supplies."))

        # Compute plan: consume from oldest supplies first
        plan = []  # list of (supply_id, take_qty)
        remaining = excess
        for s in supplies:
            if remaining <= 0:
                break
            avail = int(s.available_quantity())
            if avail <= 0:
                continue
            take = min(avail, remaining)
            plan.append((s.id, take))
            remaining -= take

        if remaining != 0:
            # should never happen if total_available computed right
            raise ValidationError(
                f"Internal inconsistency: could not plan full excess. remaining={remaining}, excess={excess}"
            )

        self.stdout.write("PLAN (consume from supplies):")
        for sid, q in plan:
            self.stdout.write(f"  supply_id={sid} consume={q}")

        if not apply:
            self.stdout.write(self.style.WARNING("DRY-RUN only. Use --apply to execute."))
            return

        # APPLY
        with transaction.atomic():
            # lock supplies rows
            locked_supplies = {
                s.id: s for s in
                StockSupply.objects.select_for_update().filter(id__in=[sid for sid, _ in plan])
            }

            # Resolve WarehouseStock for reconciliation (optional but recommended)
            ws = None
            if not no_reconcile:
                if ws_id:
                    ws = WarehouseStock.objects.select_for_update().get(pk=ws_id)
                else:
                    # try auto-detect: WarehouseStockHistory for these supplies (positive deltas)
                    ws_ids = list(
                        WarehouseStockHistory.objects
                        .filter(stock_supply__in=[locked_supplies[sid] for sid, _ in plan])
                        .values_list("warehouse_stock_id", flat=True)
                        .distinct()
                    )
                    ws_ids = [i for i in ws_ids if i is not None]
                    if len(ws_ids) == 1:
                        ws = WarehouseStock.objects.select_for_update().get(pk=ws_ids[0])
                    else:
                        raise ValidationError(
                            f"Cannot auto-detect single WarehouseStock. Found ws_ids={ws_ids}. "
                            f"Pass --warehouse-stock-id or use --no-reconcile-ws."
                        )

            # stock for sale record (always set)
            stock_obj = None
            try:
                stock_obj = Stock.objects.get(name=name)
            except Exception:
                # fallback: if Stock name differs, we still can proceed without stock, but better to keep it
                stock_obj = None

            # Create technical adjustment sell (this is what decreases available_quantity via StockSupplySell)
            adj_sell = ProductSell3.objects.create(
                customer=None,
                customer_alter_name="INVENTORY_ADJUSTMENT_CAP",
                product=getattr(stock_obj, "product", None) if stock_obj else None,
                stock=stock_obj,
                warehouse_stock=ws,
                order=None,
                quantity=excess,
                price=Decimal("0.00"),
                date=adj_date,
            )

            # Create StockSupplySell rows according to plan
            for sid, q in plan:
                s = locked_supplies[sid]
                StockSupplySell.objects.create(
                    stock_supply=s,
                    sell=adj_sell,
                    quantity=int(q),
                )
                s.refresh_used_flag(save=True)

            # Reconcile WarehouseStock.quantity to KEEP (optional)
            if ws and not no_reconcile:
                before = int(ws.quantity)
                ws.quantity = int(keep)
                ws.save(update_fields=["quantity"])

                WarehouseStockHistory.objects.create(
                    warehouse_stock=ws,
                    stock_supply=None,
                    order_settlement=None,
                    assembly=None,
                    quantity_before=before,
                    quantity_after=int(keep),
                    date=adj_date,
                    sell=adj_sell,
                )

        self.stdout.write(self.style.SUCCESS(
            f"APPLIED. Created adjustment sell_id={adj_sell.id}, consumed={excess}, keep_now={keep}."
        ))
