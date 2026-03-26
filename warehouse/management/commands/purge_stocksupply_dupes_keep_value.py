from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count, Sum
from django.db.models.functions import Coalesce

from warehouse.models import (
    StockSupply,
    WarehouseStockHistory,
    StockSupplySettlement,
    StockSupplySell,
)


class Command(BaseCommand):
    help = (
        "Purges duplicate StockSupply rows keeping the one with value>0. "
        "Deletes WarehouseStockHistory that points to removed rows (to erase trace). "
        "Rewires Settlement/Sell FK from removed -> kept (to avoid integrity issues). "
        "Does NOT change WarehouseStock quantities. Default DRY-RUN; use --apply."
    )

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Actually perform changes (otherwise dry-run).")
        parser.add_argument("--limit", type=int, default=9999, help="Max groups to process.")
        parser.add_argument("--name-contains", type=str, default="", help="Filter: StockSupply.name icontains.")
        parser.add_argument("--date-from", type=str, default="", help="Filter: date >= YYYY-MM-DD")
        parser.add_argument("--date-to", type=str, default="", help="Filter: date <= YYYY-MM-DD")

        parser.add_argument(
            "--skip-mismatch",
            action="store_true",
            help="Skip groups where delivery_item_id differs inside the duplicate group.",
        )
        parser.add_argument(
            "--force-no-valued",
            action="store_true",
            help="If no row has value>0, keep the lowest id and purge the rest (NOT recommended).",
        )

    def _qty(self, x):
        try:
            return float(x or 0)
        except Exception:
            return 0.0

    def _refs(self, ss: StockSupply):
        sell_qty = (
            StockSupplySell.objects.filter(stock_supply=ss)
            .aggregate(s=Coalesce(Sum("quantity"), 0))["s"]
        )
        settle_qty = (
            StockSupplySettlement.objects.filter(stock_supply=ss)
            .aggregate(s=Coalesce(Sum("quantity"), 0))["s"]
        )
        hist_cnt = WarehouseStockHistory.objects.filter(stock_supply=ss).count()
        return int(sell_qty), int(settle_qty), int(hist_cnt)

    def handle(self, *args, **opts):
        do_apply = bool(opts["apply"])
        limit = int(opts["limit"])
        name_contains = (opts["name_contains"] or "").strip()
        date_from = (opts["date-from"] if "date-from" in opts else opts.get("date_from", "") or "").strip()
        date_to = (opts["date-to"] if "date-to" in opts else opts.get("date_to", "") or "").strip()
        skip_mismatch = bool(opts["skip_mismatch"])
        force_no_valued = bool(opts["force_no_valued"])

        qs = StockSupply.objects.all()
        if name_contains:
            qs = qs.filter(name__icontains=name_contains)
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)

        dupes = (
            qs.values("date", "name", "quantity")
            .annotate(cnt=Count("id"))
            .filter(cnt__gt=1)
            .order_by("date", "name")
        )

        self.stdout.write(self.style.WARNING("=== PURGE STOCKSUPPLY DUPES (KEEP VALUE) ==="))
        self.stdout.write(f"Mode: {'APPLY' if do_apply else 'DRY-RUN'}")
        self.stdout.write(f"Duplicate groups: {dupes.count()}")

        processed = 0
        skipped = 0
        deleted_supply = 0
        deleted_hist = 0
        rewired_sett = 0
        rewired_sell = 0

        for d in dupes[:limit]:
            supplies = list(
                StockSupply.objects.filter(date=d["date"], name=d["name"], quantity=d["quantity"]).order_by("id")
            )
            if len(supplies) < 2:
                continue

            di_set = set([s.delivery_item_id for s in supplies])
            mismatch = len(di_set) > 1
            if mismatch and skip_mismatch:
                skipped += 1
                self.stdout.write("=" * 100)
                self.stdout.write(self.style.ERROR(
                    f"SKIP DELIVERY_ITEM_MISMATCH: date={d['date']} name={d['name']} qty={d['quantity']} di={sorted(list(di_set))}"
                ))
                continue

            valued = [s for s in supplies if self._qty(s.value) > 0]
            if len(valued) == 1:
                keep = valued[0]
            elif len(valued) > 1:
                # jeśli dwa mają value, weź ten z większą wartością, tie-break: lowest id
                keep = sorted(valued, key=lambda s: (-self._qty(s.value), s.id))[0]
            else:
                if not force_no_valued:
                    skipped += 1
                    self.stdout.write("=" * 100)
                    self.stdout.write(self.style.ERROR(
                        f"SKIP (NO VALUED ROW): date={d['date']} name={d['name']} qty={d['quantity']} ids={[s.id for s in supplies]}"
                    ))
                    continue
                keep = supplies[0]  # lowest id

            to_purge = [s for s in supplies if s.id != keep.id]

            self.stdout.write("=" * 100)
            self.stdout.write(f"GROUP: date={d['date']} name={d['name']} qty={d['quantity']} COUNT={len(supplies)}")
            self.stdout.write(self.style.SUCCESS(f"KEEP: ID={keep.id} di={keep.delivery_item_id} value={keep.value} used={keep.used}"))
            self.stdout.write(f"PURGE: {[s.id for s in to_purge]}")

            for s in supplies:
                sell_qty, settle_qty, hist_cnt = self._refs(s)
                tag = "KEEP" if s.id == keep.id else "BAD "
                self.stdout.write(
                    f"  {tag} ID={s.id} di={s.delivery_item_id} value={s.value} used={s.used} "
                    f"| refs sell={sell_qty} settle={settle_qty} hist={hist_cnt}"
                )

            if not do_apply:
                processed += 1
                continue

            with transaction.atomic():
                # lock supplies
                StockSupply.objects.select_for_update().filter(id__in=[s.id for s in supplies])

                for bad in to_purge:
                    # 1) rewire settlements/sells to keep (bez zmiany stanów)
                    c2 = StockSupplySettlement.objects.filter(stock_supply=bad).update(stock_supply=keep)
                    c3 = StockSupplySell.objects.filter(stock_supply=bad).update(stock_supply=keep)
                    rewired_sett += c2
                    rewired_sell += c3

                    # 2) delete history rows pointing to BAD (erase trace)
                    c1 = WarehouseStockHistory.objects.filter(stock_supply=bad).delete()[0]
                    deleted_hist += c1

                    # 3) delete bad supply
                    bad.delete()
                    deleted_supply += 1

            processed += 1

        self.stdout.write("=" * 100)
        self.stdout.write(f"Processed groups: {processed} (limit={limit})")
        self.stdout.write(f"Skipped groups: {skipped}")
        if do_apply:
            self.stdout.write(self.style.WARNING("--- STATS ---"))
            self.stdout.write(f"WarehouseStockHistory deleted: {deleted_hist}")
            self.stdout.write(f"StockSupplySettlement rewired: {rewired_sett}")
            self.stdout.write(f"StockSupplySell rewired: {rewired_sell}")
            self.stdout.write(f"StockSupply deleted: {deleted_supply}")
        self.stdout.write(self.style.WARNING("=== END ==="))
