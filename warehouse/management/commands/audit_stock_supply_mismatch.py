import datetime
from collections import defaultdict
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db.models import OuterRef, Subquery, IntegerField, Sum
from django.db.models.functions import Coalesce

from warehouse.models import (
    WarehouseStock,
    WarehouseStockHistory,
    StockSupply,
    StockSupplySettlement,
    StockSupplySell,
)


class Command(BaseCommand):
    help = "Audyt zgodności: WarehouseStockHistory (ALL) vs StockSupply remaining qty na daną datę."

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            type=str,
            default=None,
            help="Data audytu YYYY-MM-DD (domyślnie: dziś).",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=200,
            help="Ile rekordów wypisać (domyślnie 200).",
        )
        parser.add_argument(
            "--min-diff",
            type=int,
            default=1,
            help="Minimalna bezwzględna różnica do pokazania (domyślnie 1).",
        )
        parser.add_argument(
            "--only-stocktype-id",
            type=int,
            default=None,
            help="Filtruj tylko po stock_type_id (opcjonalnie).",
        )
        parser.add_argument(
            "--only-name-contains",
            type=str,
            default=None,
            help="Filtruj po fragmencie nazwy (opcjonalnie, case-insensitive).",
        )
        parser.add_argument(
            "--top-warehouses",
            type=int,
            default=5,
            help="Ile magazynów pokazać w breakdown (domyślnie 5).",
        )

    def handle(self, *args, **options):
        date_str = options["date"]
        if date_str:
            audit_date = datetime.date.fromisoformat(date_str)
        else:
            audit_date = datetime.date.today()

        limit = options["limit"]
        min_diff = options["min_diff"]
        only_stocktype_id = options["only_stocktype_id"]
        name_contains = options["only_name_contains"]
        top_wh = options["top_warehouses"]

        self.stdout.write(self.style.MIGRATE_HEADING(f"=== AUDIT STOCK MISMATCH @ {audit_date} ==="))

        # ------------------------------------------------------------
        # 1) WS qty @ date (ALL warehouses): bierzemy last history <= date
        # ------------------------------------------------------------
        end_hist = (
            WarehouseStockHistory.objects
            .filter(warehouse_stock=OuterRef("pk"), date__lte=audit_date)
            .order_by("-date", "-id")
        )

        ws_qs = (
            WarehouseStock.objects
            .select_related("warehouse", "stock", "stock__stock_type")
            .annotate(ws_qty=Coalesce(Subquery(end_hist.values("quantity_after")[:1]), 0, output_field=IntegerField()))
        )

        if only_stocktype_id is not None:
            ws_qs = ws_qs.filter(stock__stock_type_id=only_stocktype_id)
        if name_contains:
            ws_qs = ws_qs.filter(stock__name__icontains=name_contains)

        ws_rows = list(ws_qs.only("id", "warehouse_id", "warehouse__name", "stock__name", "stock__stock_type_id", "ws_qty"))

        # mapy: key -> qty oraz breakdown key-> list(warehouse, qty)
        ws_all_by_key = defaultdict(int)
        ws_breakdown_by_key = defaultdict(list)

        for ws in ws_rows:
            qty = int(ws.ws_qty or 0)
            if qty == 0:
                continue
            key = (ws.stock.stock_type_id, ws.stock.name)
            ws_all_by_key[key] += qty
            ws_breakdown_by_key[key].append((ws.warehouse.name, qty))

        # ------------------------------------------------------------
        # 2) Supplies remaining qty @ date: supply.qty - settled_to_date - sold_to_date
        # ------------------------------------------------------------
        supplies_qs = StockSupply.objects.filter(date__lte=audit_date)

        if only_stocktype_id is not None:
            supplies_qs = supplies_qs.filter(stock_type_id=only_stocktype_id)
        if name_contains:
            supplies_qs = supplies_qs.filter(name__icontains=name_contains)

        supplies = list(supplies_qs.only("id", "stock_type_id", "name", "quantity"))

        supply_ids = [s.id for s in supplies]

        settled_map = {}
        sold_map = {}

        if supply_ids:
            settled_map = {
                row["stock_supply_id"]: int(row["s"] or 0)
                for row in (
                    StockSupplySettlement.objects
                    .filter(
                        stock_supply_id__in=supply_ids,
                        as_result=False,
                        settlement__settlement_date__lte=audit_date,
                    )
                    .values("stock_supply_id")
                    .annotate(s=Sum("quantity"))
                )
            }

            sold_map = {
                row["stock_supply_id"]: int(row["s"] or 0)
                for row in (
                    StockSupplySell.objects
                    .filter(
                        stock_supply_id__in=supply_ids,
                        sell__date__lte=audit_date,
                    )
                    .values("stock_supply_id")
                    .annotate(s=Sum("quantity"))
                )
            }

        supplies_remaining_by_key = defaultdict(int)

        for s in supplies:
            qty = int(s.quantity or 0)
            if qty <= 0:
                continue
            used = settled_map.get(s.id, 0) + sold_map.get(s.id, 0)
            remaining = qty - used
            if remaining <= 0:
                continue
            key = (s.stock_type_id, s.name)
            supplies_remaining_by_key[key] += remaining

        # ------------------------------------------------------------
        # 3) Porównanie: union keys
        # ------------------------------------------------------------
        keys = set(ws_all_by_key.keys()) | set(supplies_remaining_by_key.keys())

        mismatches = []
        for key in keys:
            ws_qty = int(ws_all_by_key.get(key, 0))
            sup_qty = int(supplies_remaining_by_key.get(key, 0))
            diff = sup_qty - ws_qty  # >0: partie > WS, <0: WS > partie
            if abs(diff) < min_diff:
                continue

            breakdown = ws_breakdown_by_key.get(key, [])
            breakdown.sort(key=lambda x: x[1], reverse=True)
            breakdown = breakdown[:top_wh]

            reason = "SUPPLIES>WS (partie bez magazynu?)" if diff > 0 else "WS>SUPPLIES (stan bez partii?)"

            mismatches.append({
                "stock_type_id": key[0],
                "name": key[1],
                "ws_qty": ws_qty,
                "sup_qty": sup_qty,
                "diff": diff,
                "reason": reason,
                "breakdown": breakdown,
            })

        mismatches.sort(key=lambda r: abs(r["diff"]), reverse=True)

        self.stdout.write(self.style.WARNING(f"Mismatch count: {len(mismatches)} (showing top {min(limit, len(mismatches))})"))
        self.stdout.write("")

        # ------------------------------------------------------------
        # 4) Druk
        # ------------------------------------------------------------
        for i, r in enumerate(mismatches[:limit], start=1):
            self.stdout.write(self.style.MIGRATE_LABEL(f"[{i}] stock_type_id={r['stock_type_id']}  name={r['name']}"))
            self.stdout.write(f"    WS qty @date:      {r['ws_qty']}")
            self.stdout.write(f"    Supplies remaining:{r['sup_qty']}")
            self.stdout.write(f"    Diff (sup-ws):     {r['diff']}   -> {r['reason']}")
            if r["breakdown"]:
                b = ", ".join([f"{wh}:{qty}" for wh, qty in r["breakdown"]])
                self.stdout.write(f"    Warehouses (top):  {b}")
            self.stdout.write("")

        self.stdout.write(self.style.SUCCESS("=== END AUDIT ==="))
