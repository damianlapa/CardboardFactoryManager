from django.core.management.base import BaseCommand
from django.db.models import Count, Sum
from django.db.models.functions import Coalesce

from warehouse.models import (
    StockSupply,
    StockSupplySell,
    StockSupplySettlement,
    WarehouseStockHistory,
)


class Command(BaseCommand):
    help = "Detailed audit of duplicate StockSupply rows + KEEP/DELETE recommendation (NO changes)."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=200, help="Max duplicate groups to print.")
        parser.add_argument("--name-contains", type=str, default="", help="Filter: StockSupply.name contains (icontains).")
        parser.add_argument("--date-from", type=str, default="", help="Filter: date >= YYYY-MM-DD")
        parser.add_argument("--date-to", type=str, default="", help="Filter: date <= YYYY-MM-DD")
        parser.add_argument("--only-safe", action="store_true", help="Print only groups that look safe to auto-dedupe.")
        parser.add_argument("--only-risk", action="store_true", help="Print only risky groups.")

    def _refs_for_supply(self, ss: StockSupply):
        sell_qty = (
            StockSupplySell.objects
            .filter(stock_supply=ss)
            .aggregate(s=Coalesce(Sum("quantity"), 0))["s"]
        )
        settle_qty = (
            StockSupplySettlement.objects
            .filter(stock_supply=ss)
            .aggregate(s=Coalesce(Sum("quantity"), 0))["s"]
        )
        hist_cnt = WarehouseStockHistory.objects.filter(stock_supply=ss).count()

        # “twarde” referencje (czyli coś faktycznie wskazuje na ten rekord)
        has_refs = (int(sell_qty) > 0) or (int(settle_qty) > 0) or (int(hist_cnt) > 0)

        return {
            "sell_qty": int(sell_qty),
            "settle_qty": int(settle_qty),
            "hist_cnt": int(hist_cnt),
            "has_refs": bool(has_refs),
        }

    def _recommend(self, supplies):
        """
        Zwraca dict:
        - keep_id
        - delete_ids
        - safe (bool)
        - reason
        - flags (list[str])
        """
        flags = []
        supplies = list(supplies)

        # Delivery item mismatch = ryzyko (przykład u Ciebie: ten sam (date,name,qty) ale różne delivery_item_id)
        di_set = set([s.delivery_item_id for s in supplies])
        if len(di_set) > 1:
            flags.append("DELIVERY_ITEM_MISMATCH")

        rows = []
        for s in supplies:
            refs = self._refs_for_supply(s)
            rows.append((s, refs))

        # Rozdziel: z referencjami vs bez
        with_refs = [x for x in rows if x[1]["has_refs"]]
        no_refs = [x for x in rows if not x[1]["has_refs"]]

        # Jeśli dokładnie jeden ma referencje -> KEEP ten, DELETE reszta (bezpieczne)
        if len(with_refs) == 1:
            keep = with_refs[0][0]
            delete_ids = [s.id for s, _ in no_refs]
            safe = (len(flags) == 0)
            reason = "Only one row has references; keep referenced one."
            return {"keep_id": keep.id, "delete_ids": delete_ids, "safe": safe, "reason": reason, "flags": flags}

        # Jeśli wiele ma referencje -> wymaga MERGE (przepięcia FK) => nie auto
        if len(with_refs) > 1:
            flags.append("MULTIPLE_REFERENCED_ROWS")
            # umownie KEEP: ten z największą liczbą referencji (tylko jako sugestia)
            def score(item):
                _, r = item
                return (r["sell_qty"] + r["settle_qty"] + r["hist_cnt"], -item[0].id)

            keep = sorted(with_refs, key=score, reverse=True)[0][0]
            delete_ids = [s.id for s, _ in rows if s.id != keep.id]
            return {
                "keep_id": keep.id,
                "delete_ids": delete_ids,
                "safe": False,
                "reason": "More than one row has references -> requires MERGE (rewire FK), not safe auto-delete.",
                "flags": flags,
            }

        # Jeśli żaden nie ma referencji -> wybieramy “najbardziej sensowny”:
        # 1) value > 0
        # 2) used=False (mniej podejrzane)
        # 3) lowest id (stabilnie)
        def pref(s: StockSupply):
            return (
                1 if (s.value and float(s.value) > 0) else 0,
                1 if (s.used is False) else 0,
                -s.id,  # uwaga: tu -id aby po sort(reverse=True) preferować mniejsze id? -> lepiej jawnie:
            )

        # zrobimy jawnie: sortujemy tak, aby wygrało value>0, used=False, a potem MIN id
        supplies_sorted = sorted(
            supplies,
            key=lambda s: (
                0 if (s.value and float(s.value) > 0) else 1,  # 0 lepsze
                0 if (s.used is False) else 1,                  # 0 lepsze
                s.id,                                           # mniejsze lepsze
            )
        )
        keep = supplies_sorted[0]
        delete_ids = [s.id for s in supplies if s.id != keep.id]
        safe = (len(flags) == 0)
        reason = "No references; keep row with value>0 / used=False preference, else lowest id."
        return {"keep_id": keep.id, "delete_ids": delete_ids, "safe": safe, "reason": reason, "flags": flags}

    def handle(self, *args, **options):
        limit = options["limit"]
        name_contains = (options["name_contains"] or "").strip()
        date_from = (options["date_from"] or "").strip()
        date_to = (options["date_to"] or "").strip()
        only_safe = bool(options["only_safe"])
        only_risk = bool(options["only_risk"])

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
            .order_by("-cnt", "date", "name")
        )

        total_groups = dupes.count()
        self.stdout.write(self.style.WARNING("=== STOCKSUPPLY DUPLICATE DETAIL AUDIT ==="))
        self.stdout.write(f"Duplicate groups found: {total_groups}")

        if total_groups == 0:
            self.stdout.write(self.style.SUCCESS("No duplicates found."))
            self.stdout.write(self.style.WARNING("=== END ==="))
            return

        shown = 0
        safe_count = 0
        risk_count = 0

        for d in dupes[:limit]:
            supplies = StockSupply.objects.filter(
                date=d["date"],
                name=d["name"],
                quantity=d["quantity"],
            ).order_by("id")

            rec = self._recommend(supplies)

            if rec["safe"]:
                safe_count += 1
            else:
                risk_count += 1

            if only_safe and not rec["safe"]:
                continue
            if only_risk and rec["safe"]:
                continue

            shown += 1
            self.stdout.write("=" * 100)
            self.stdout.write(
                f"date={d['date']} | name={d['name']} | qty={d['quantity']} | COUNT={d['cnt']}"
            )
            self.stdout.write(
                f"RECOMMEND: KEEP={rec['keep_id']} DELETE={rec['delete_ids']} | SAFE={rec['safe']} | {rec['reason']}"
            )
            if rec["flags"]:
                self.stdout.write("FLAGS: " + ", ".join(rec["flags"]))

            # print rows + refs
            for s in supplies:
                refs = self._refs_for_supply(s)
                self.stdout.write(
                    f"  ID={s.id} di={s.delivery_item_id} value={s.value} used={s.used} | "
                    f"refs: sell_qty={refs['sell_qty']} settle_qty={refs['settle_qty']} hist_cnt={refs['hist_cnt']}"
                )

        self.stdout.write("=" * 100)
        self.stdout.write(f"Shown groups: {shown} / {min(total_groups, limit)}")
        self.stdout.write(f"SAFE groups (heuristic): {safe_count}")
        self.stdout.write(f"RISK groups: {risk_count}")
        self.stdout.write(self.style.WARNING("=== END ==="))
