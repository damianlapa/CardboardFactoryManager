# warehouse/monthly_reports_views.py

import calendar
import datetime
import re
from decimal import Decimal, ROUND_HALF_UP

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import OuterRef, Subquery, IntegerField, Sum, F, ExpressionWrapper, DecimalField
from django.db.models.functions import Coalesce
from django.shortcuts import render
from django.views import View

from warehouse.models import (
    Warehouse,
    WarehouseStock,
    WarehouseStockHistory,
    StockSupply,
    StockSupplySettlement,
    StockSupplySell,
    ProductSell3,
)

DEBUG_STOCKS = [
    ("MERIDA | BC | KÓŁKA", 34),
    ("TFP T5BC1PWP0749[1600x470]", 1),
    ("FIBRO | B | 1050x470", 34),
    ("TFP T30B1TWT0341[1050x470]", 1),
    ("AQ 3B450A2[1939x612]", 1),
]


WAREHOUSE_MAIN = "MAGAZYN GŁÓWNY"
WAREHOUSE_FG = "MAGAZYN WYROBÓW GOTOWYCH"
WAREHOUSE_AUX = "MAGAZYN MATERIAŁÓW POMOCNICZYCH"
WAREHOUSE_CLEARANCE = "MAGAZYN WYPRZEDAŻOWY"
WAREHOUSE_MAINTENANCE = "MAGAZYN CZĘŚCI"

WAREHOUSE_NAMES = [
    WAREHOUSE_MAIN,
    WAREHOUSE_FG,
    WAREHOUSE_AUX,
    WAREHOUSE_CLEARANCE,
    WAREHOUSE_MAINTENANCE,
]

# Jeśli u Ciebie tektura ma inny typ niż "material", zmień tutaj (w jednym miejscu).
CARDBOARD_STOCKTYPE = "material"


def month_range(year: int, month: int) -> tuple[datetime.date, datetime.date]:
    start = datetime.date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    end = datetime.date(year, month, last_day)
    return start, end


def dims_to_m2(dim_str: str | None) -> Decimal:
    """Przyjmuje np. '1200x800' (mm) i zwraca m² na 1 sztukę."""
    if not dim_str:
        return Decimal("0")

    s = dim_str.lower().replace(" ", "")
    m = re.search(r"(\d+)x(\d+)", s)
    if not m:
        return Decimal("0")

    a = Decimal(m.group(1))
    b = Decimal(m.group(2))
    return (a * b / Decimal("1000000")).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)


def supply_effective_dimensions(ss: StockSupply) -> str | None:
    """Bierze ss.dimensions, a jeśli brak, próbuje z DeliveryItem.order.dimensions."""
    if ss.dimensions:
        return ss.dimensions
    if ss.delivery_item_id and ss.delivery_item and ss.delivery_item.order:
        return ss.delivery_item.order.dimensions
    return None


def supplies_value_at_date_for_keys(
    keys: set[tuple[int, str]],
    date_point: datetime.date
) -> tuple[dict[tuple[int, str], Decimal], dict[int, dict], dict[tuple[int, str], int]]:
    """
    Wycena stanów na konkretną datę (po partiach StockSupply).

    Zwraca:
      - value_map: (stock_type_id, name) -> remaining_value_at_date
      - debug_supply: supply_id -> szczegóły obliczeń
      - qty_map: (stock_type_id, name) -> remaining_qty_at_date  (sumarycznie po partiach)
    """

    if not keys:
        return {}, {}, {}

    stock_type_ids = sorted({k[0] for k in keys})
    names = sorted({k[1] for k in keys})

    supplies = list(
        StockSupply.objects
        .filter(stock_type_id__in=stock_type_ids, name__in=names, date__lte=date_point)
        .only("id", "stock_type_id", "name", "quantity", "value", "date", "dimensions", "delivery_item_id")
        .select_related("delivery_item", "delivery_item__order")
    )

    supply_ids = [s.id for s in supplies]
    if not supply_ids:
        return {}, {}, {}

    settled_map = {
        row["stock_supply_id"]: int(row["s"] or 0)
        for row in (
            StockSupplySettlement.objects
            .filter(stock_supply_id__in=supply_ids, as_result=False, settlement__settlement_date__lte=date_point)
            .values("stock_supply_id")
            .annotate(s=Sum("quantity"))
        )
    }

    from maintenance.models import MaintenancePartUsageSupply
    maintenance_map = {
        row["stock_supply_id"]: int(row["s"] or 0)
        for row in (
            MaintenancePartUsageSupply.objects
            .filter(
                stock_supply_id__in=supply_ids,
                usage__event__date__lte=date_point
            )
            .values("stock_supply_id")
            .annotate(s=Sum("quantity"))
        )
    }

    sold_map = {
        row["stock_supply_id"]: int(row["s"] or 0)
        for row in (
            StockSupplySell.objects
            .filter(stock_supply_id__in=supply_ids, sell__date__lte=date_point)
            .values("stock_supply_id")
            .annotate(s=Sum("quantity"))
        )
    }

    value_map: dict[tuple[int, str], Decimal] = {}
    qty_map: dict[tuple[int, str], int] = {}
    debug_supply: dict[int, dict] = {}

    for s in supplies:
        qty = int(s.quantity or 0)
        if qty <= 0:
            continue

        settled = settled_map.get(s.id, 0)
        sold = sold_map.get(s.id, 0)
        maintenance_used = maintenance_map.get(s.id, 0)
        used = settled + sold + maintenance_used

        overused = used > qty
        remaining_raw = qty - used  # może być ujemne
        remaining = max(0, remaining_raw)

        value = Decimal(s.value or 0)
        rem_value = Decimal("0.00")
        if remaining > 0:
            rem_value = (value * Decimal(remaining) / Decimal(qty)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        key = (s.stock_type_id, s.name)

        if remaining > 0:
            value_map[key] = value_map.get(key, Decimal("0.00")) + rem_value
            qty_map[key] = qty_map.get(key, 0) + remaining
        else:
            qty_map.setdefault(key, 0)

        dim = supply_effective_dimensions(s)
        debug_supply[s.id] = {
            "supply_id": s.id,
            "date": s.date,
            "name": s.name,
            "stock_type_id": s.stock_type_id,
            "qty": qty,
            "value": value,
            "settled_qty": settled,
            "sold_qty": sold,
            "used_qty": used,
            "remaining_qty_raw": remaining_raw,
            "remaining_qty": remaining,
            "remaining_value": rem_value,
            "overused": overused,
            "dimensions": dim,
            "m2_per_unit": dims_to_m2(dim),
        }

    # zaokrąglij sumaryczne wartości (dla czytelności)
    for k in list(value_map.keys()):
        value_map[k] = value_map[k].quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return value_map, debug_supply, qty_map


class MonthlyWarehouseReportView(LoginRequiredMixin, View):
    template_name = "warehouse/monthly_report.html"

    def _parse_year_month(self, request) -> tuple[int, int]:
        today = datetime.date.today()
        year = int(request.GET.get("year") or today.year)
        month = int(request.GET.get("month") or today.month)
        month = max(1, min(12, month))
        return year, month

    def get(self, request):
        year, month = self._parse_year_month(request)
        start_date, end_date = month_range(year, month)
        debug = request.GET.get("debug") == "1"

        warehouses = list(Warehouse.objects.filter(name__in=WAREHOUSE_NAMES))
        wh_by_name = {w.name: w for w in warehouses}
        missing = [n for n in WAREHOUSE_NAMES if n not in wh_by_name]
        if missing:
            raise ValueError(f"Brak magazynów w DB: {missing}")

        wh_main = wh_by_name[WAREHOUSE_MAIN]

        ws_qs = (
            WarehouseStock.objects
            .select_related("warehouse", "stock", "stock__stock_type")
            .filter(warehouse__in=warehouses)
        )

        # --- ilości (start/end) z historii magazynu ---
        start_hist = (
            WarehouseStockHistory.objects
            .filter(warehouse_stock=OuterRef("pk"), date__lt=start_date)
            .order_by("-date", "-id")
        )
        end_hist = (
            WarehouseStockHistory.objects
            .filter(warehouse_stock=OuterRef("pk"), date__lte=end_date)
            .order_by("-date", "-id")
        )

        ws_qs = ws_qs.annotate(
            start_qty=Coalesce(Subquery(start_hist.values("quantity_after")[:1]), 0, output_field=IntegerField()),
            end_qty=Coalesce(Subquery(end_hist.values("quantity_after")[:1]), 0, output_field=IntegerField()),
        ).annotate(
            diff_qty=F("end_qty") - F("start_qty")
        )

        # --- tektura: przyjęcia (m² + wartość) ---
        received_supplies_qs = (
            StockSupply.objects
            .select_related("stock_type", "delivery_item", "delivery_item__order")
            .filter(
                stock_type__stock_type=CARDBOARD_STOCKTYPE,
                date__gte=start_date,
                date__lte=end_date,
            )
        )
        received_supplies = list(received_supplies_qs)

        received_material_value = received_supplies_qs.aggregate(
            s=Coalesce(Sum("value"), Decimal("0.00"))
        )["s"]

        received_material_m2 = Decimal("0.000")
        received_debug_rows = []
        missing_dims_received = []
        for ss in received_supplies:
            dim = supply_effective_dimensions(ss)
            m2_unit = dims_to_m2(dim)
            qty = int(ss.quantity or 0)
            m2_total = (Decimal(qty) * m2_unit).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
            received_material_m2 += m2_total

            if qty > 0 and m2_unit == 0:
                missing_dims_received.append(ss.id)

            if debug:
                received_debug_rows.append({
                    "id": ss.id,
                    "date": ss.date,
                    "name": ss.name,
                    "qty": qty,
                    "value": Decimal(ss.value or 0),
                    "dimensions": dim,
                    "m2_per_unit": m2_unit,
                    "m2_total": m2_total,
                })

        received_material_m2 = received_material_m2.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)

        # --- tektura: zużycie w produkcji (m² + wartość) ---
        used_settlements_qs = (
            StockSupplySettlement.objects
            .select_related(
                "stock_supply",
                "stock_supply__delivery_item",
                "stock_supply__delivery_item__order",
                "settlement",
                "settlement__material",
                "settlement__material__warehouse",
            )
            .filter(
                as_result=False,
                stock_supply__stock_type__stock_type=CARDBOARD_STOCKTYPE,
                settlement__settlement_date__gte=start_date,
                settlement__settlement_date__lte=end_date,
                settlement__material__warehouse=wh_main,
            )
        )
        used_settlements = list(used_settlements_qs)

        processed_material_value = used_settlements_qs.aggregate(
            s=Coalesce(Sum("value"), Decimal("0.00"))
        )["s"]

        processed_material_m2 = Decimal("0.000")
        used_debug_rows = []
        missing_dims_used = []
        for row in used_settlements:
            dim = supply_effective_dimensions(row.stock_supply)
            m2_unit = dims_to_m2(dim)
            qty_used = int(row.quantity or 0)
            m2_total = (Decimal(qty_used) * m2_unit).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
            processed_material_m2 += m2_total

            if qty_used > 0 and m2_unit == 0:
                missing_dims_used.append(row.stock_supply_id)

            if debug:
                used_debug_rows.append({
                    "settlement_id": row.settlement_id,
                    "settlement_date": row.settlement.settlement_date if row.settlement_id else None,
                    "supply_id": row.stock_supply_id,
                    "supply_name": row.stock_supply.name if row.stock_supply_id else None,
                    "qty_used": qty_used,
                    "value_used": Decimal(row.value or 0),
                    "dimensions": dim,
                    "m2_per_unit": m2_unit,
                    "m2_total": m2_total,
                })

        processed_material_m2 = processed_material_m2.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)

        # --- sprzedaż ---
        sales_qs = ProductSell3.objects.filter(date__gte=start_date, date__lte=end_date)

        revenue_expr = ExpressionWrapper(
            F("price") * F("quantity"),
            output_field=DecimalField(max_digits=18, decimal_places=2),
        )
        sales_revenue = sales_qs.aggregate(
            s=Coalesce(Sum(revenue_expr), Decimal("0.00"))
        )["s"]

        sales = list(sales_qs.select_related("customer"))
        sales_cogs = sum((s.cogs() for s in sales), Decimal("0.00")).quantize(Decimal("0.01"))
        sales_profit = (sales_revenue - sales_cogs).quantize(Decimal("0.01"))

        profit_per_m2 = None
        if processed_material_m2 > 0:
            profit_per_m2 = (sales_profit / processed_material_m2).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

        # --- wartość magazynów na daty (po partiach) ---
        keys = {(ws.stock.stock_type_id, ws.stock.name) for ws in ws_qs}
        open_date_point = start_date - datetime.timedelta(days=1)

        value_start_map, value_start_debug, qty_start_map = supplies_value_at_date_for_keys(keys, open_date_point)
        value_end_map, value_end_debug, qty_end_map = supplies_value_at_date_for_keys(keys, end_date)

        def value_for_warehouse(warehouse_obj: Warehouse, mp: dict[tuple[int, str], Decimal]) -> Decimal:
            total = Decimal("0.00")
            for ws in ws_qs:
                if ws.warehouse_id != warehouse_obj.id:
                    continue
                total += mp.get((ws.stock.stock_type_id, ws.stock.name), Decimal("0.00"))
            return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        warehouse_values = []
        total_value_start = Decimal("0.00")
        total_value_end = Decimal("0.00")

        for w in warehouses:
            v_start = value_for_warehouse(w, value_start_map)
            v_end = value_for_warehouse(w, value_end_map)
            v_diff = (v_end - v_start).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            warehouse_values.append({
                "name": w.name,
                "start": v_start,
                "end": v_end,
                "diff": v_diff,
            })

            total_value_start += v_start
            total_value_end += v_end

        total_value_start = total_value_start.quantize(Decimal("0.01"))
        total_value_end = total_value_end.quantize(Decimal("0.01"))
        total_value_diff = (total_value_end - total_value_start).quantize(Decimal("0.01"))

        # ---------------------------------------------------------------------
        # KONTROLE SPÓJNOŚCI (najważniejsze do zaufania do raportu)
        # ---------------------------------------------------------------------

        # 1) FIFO kompletność sprzedaży
        sales_ids = [s.id for s in sales]
        fifo_map = {
            row["sell_id"]: int(row["s"] or 0)
            for row in (
                StockSupplySell.objects
                .filter(sell_id__in=sales_ids)
                .values("sell_id")
                .annotate(s=Sum("quantity"))
            )
        }
        sales_fifo_issues = []
        for s in sales:
            fifo_qty = fifo_map.get(s.id, 0)
            expected = int(s.quantity or 0)
            if fifo_qty != expected:
                sales_fifo_issues.append({
                    "sell_id": s.id,
                    "date": s.date,
                    "customer": getattr(s.customer, "name", str(s.customer)) if getattr(s, "customer", None) else "",
                    "product": getattr(s, "product", None).name if getattr(s, "product", None) else "",
                    "expected_qty": expected,
                    "fifo_qty": fifo_qty,
                    "diff": fifo_qty - expected,
                })

        # 2) Partie przerochowane (used > qty) — sprawdzamy na END
        overused_supplies = [
            d for d in value_end_debug.values()
            if d.get("overused")
        ]

        # 3) Missing/nieparsowalne dimensions (m²=0)
        missing_dimensions_received_count = len(set(missing_dims_received))
        missing_dimensions_used_count = len(set(missing_dims_used))

        # 4) Zgodność stanów: WSZYSTKIE magazyny vs partie (end_date)
        # Ten test ma sens, bo StockSupply nie ma magazynu -> to jest globalny stan "po partiach".

        # suma stanów na end_date dla WSZYSTKICH magazynów (nie tylko tych 4)
        all_ws_end = (
            WarehouseStock.objects
            .select_related("stock", "stock__stock_type", "warehouse")
            .annotate(
                end_qty_all=Coalesce(Subquery(
                    WarehouseStockHistory.objects
                    .filter(warehouse_stock=OuterRef("pk"), date__lte=end_date)
                    .order_by("-date", "-id")
                    .values("quantity_after")[:1]
                ), 0, output_field=IntegerField())
            )
        )

        # mapy: key -> total qty (all warehouses) oraz key -> qty w magazynach raportu
        ws_all_end_by_key: dict[tuple[int, str], int] = {}
        ws_report_end_by_key: dict[tuple[int, str], int] = {}

        # oraz: key -> breakdown magazynów spoza raportu (do podglądu)
        ws_outside_breakdown: dict[tuple[int, str], list[dict]] = {}

        report_wh_ids = {w.id for w in warehouses}

        for ws in all_ws_end:
            key = (ws.stock.stock_type_id, ws.stock.name)
            q = int(ws.end_qty_all or 0)
            if q == 0:
                continue

            ws_all_end_by_key[key] = ws_all_end_by_key.get(key, 0) + q

            if ws.warehouse_id in report_wh_ids:
                ws_report_end_by_key[key] = ws_report_end_by_key.get(key, 0) + q
            else:
                ws_outside_breakdown.setdefault(key, []).append({
                    "warehouse": ws.warehouse.name,
                    "qty": q,
                })

        # porównanie: ALL warehouses vs supplies remaining qty
        qty_mismatch_rows = []
        for key, ws_qty_all in ws_all_end_by_key.items():
            supply_qty = int(qty_end_map.get(key, 0))
            if ws_qty_all != supply_qty:
                outside = ws_outside_breakdown.get(key, [])
                outside_sorted = sorted(outside, key=lambda x: x["qty"], reverse=True)[:10]
                outside_sum = sum(x["qty"] for x in outside_sorted)

                qty_mismatch_rows.append({
                    "stock_type_id": key[0],
                    "name": key[1],

                    "warehouse_qty_end_all": ws_qty_all,
                    "warehouse_qty_end_report": int(ws_report_end_by_key.get(key, 0)),
                    "supply_qty_end": supply_qty,

                    "diff_all": supply_qty - ws_qty_all,
                    "diff_report": supply_qty - int(ws_report_end_by_key.get(key, 0)),

                    "outside_top": outside_sorted,
                    "outside_top_sum": outside_sum,
                    "outside_count": len(outside),
                })

        # sortowanie: największe rozjazdy na górę
        qty_mismatch_rows.sort(key=lambda r: abs(r["diff_all"]), reverse=True)


        # ---------------------------------------------------------------------
        # DEBUG: tabele źródłowe
        # ---------------------------------------------------------------------
        value_start_debug_rows = []
        value_end_debug_rows = []
        if debug:
            value_start_debug_rows = sorted(value_start_debug.values(), key=lambda d: (str(d["date"]), d["name"], d["supply_id"]))
            value_end_debug_rows = sorted(value_end_debug.values(), key=lambda d: (str(d["date"]), d["name"], d["supply_id"]))

        rows = [
            {
                "warehouse": ws.warehouse.name,
                "stock": ws.stock.name,
                "unit": ws.stock.stock_type.unit,
                "start_qty": ws.start_qty,
                "end_qty": ws.end_qty,
                "diff_qty": ws.diff_qty,
            }
            for ws in ws_qs
            if (ws.start_qty or ws.end_qty or ws.diff_qty)
        ]

        # ---------------------------------------------------------------------
        # SZCZEGÓŁOWA ANALIZA WYBRANYCH POZYCJI
        # ---------------------------------------------------------------------

        selected_stock_analysis = []

        for name, stock_type_id in DEBUG_STOCKS:

            # 1️⃣ wszystkie partie do end_date
            supplies = list(
                StockSupply.objects
                .filter(
                    name=name,
                    stock_type_id=stock_type_id,
                    date__lte=end_date
                )
            )

            supply_ids = [s.id for s in supplies]

            total_supply_qty = sum(int(s.quantity or 0) for s in supplies)
            total_supply_value = sum(Decimal(s.value or 0) for s in supplies)

            # 2️⃣ settled (TYLKO rozchód) do end_date
            settled_map = {
                row["stock_supply_id"]: int(row["s"] or 0)
                for row in (
                    StockSupplySettlement.objects
                    .filter(
                        stock_supply_id__in=supply_ids,
                        as_result=False,
                        settlement__settlement_date__lte=end_date,
                    )
                    .values("stock_supply_id")
                    .annotate(s=Sum("quantity"))
                )
            }

            # 3️⃣ sold do end_date
            sold_map = {
                row["stock_supply_id"]: int(row["s"] or 0)
                for row in (
                    StockSupplySell.objects
                    .filter(
                        stock_supply_id__in=supply_ids,
                        sell__date__lte=end_date,
                    )
                    .values("stock_supply_id")
                    .annotate(s=Sum("quantity"))
                )
            }

            total_settled = sum(settled_map.values())
            total_sold = sum(sold_map.values())

            # remaining nie może być ujemne w sensie "co leży" -> ale ujemne to sygnał błędu danych
            remaining_raw = total_supply_qty - total_settled - total_sold
            total_remaining = max(0, remaining_raw)

            # 4️⃣ WarehouseStock ALL magazyny
            ws_rows = (
                WarehouseStock.objects
                .select_related("warehouse", "stock", "stock__stock_type")
                .filter(
                    stock__name=name,
                    stock__stock_type_id=stock_type_id
                )
            )

            ws_total_qty = 0
            ws_breakdown = []

            # 5️⃣ Analiza historii magazynu (co naprawdę działo się w WS)
            hist = (
                WarehouseStockHistory.objects
                .select_related("sell", "order_settlement", "stock_supply", "assembly")
                .filter(
                    warehouse_stock__stock__name=name,
                    warehouse_stock__stock__stock_type_id=stock_type_id,
                    date__lte=end_date,
                )
                .only("quantity_before", "quantity_after", "sell_id", "order_settlement_id", "stock_supply_id",
                      "assembly_id", "date")
            )

            sum_in = 0
            sum_out_sell = 0
            sum_out_settle = 0
            sum_out_other = 0
            in_without_supply = 0

            for h in hist:
                delta = int(h.quantity_after) - int(h.quantity_before)
                if delta > 0:
                    sum_in += delta
                    if not h.stock_supply_id:
                        in_without_supply += delta
                elif delta < 0:
                    out = -delta
                    if h.sell_id:
                        sum_out_sell += out
                    elif h.order_settlement_id:
                        sum_out_settle += out
                    else:
                        sum_out_other += out



            for ws in ws_rows:
                end_qty = (
                    WarehouseStockHistory.objects
                    .filter(warehouse_stock=ws, date__lte=end_date)
                    .order_by("-date", "-id")
                    .values_list("quantity_after", flat=True)
                    .first()
                )
                end_qty = int(end_qty or 0)

                if end_qty != 0:
                    ws_total_qty += end_qty
                    ws_breakdown.append({
                        "warehouse": ws.warehouse.name,
                        "qty": end_qty
                    })

            selected_stock_analysis.append({
                "ws_hist_in": sum_in,
                "ws_hist_out_sell": sum_out_sell,
                "ws_hist_out_settle": sum_out_settle,
                "ws_hist_out_other": sum_out_other,
                "ws_hist_in_without_supply": in_without_supply,
                "name": name,
                "stock_type_id": stock_type_id,
                "remaining_raw": remaining_raw,
                "overused": remaining_raw < 0,

                "supplies_count": len(supplies),
                "supply_total_qty": total_supply_qty,
                "supply_total_value": total_supply_value,
                "settled_total": total_settled,
                "sold_total": total_sold,
                "remaining_from_supplies": total_remaining,

                "warehouse_total_qty": ws_total_qty,
                "warehouse_breakdown": ws_breakdown,
            })

        context = {
            "selected_stock_analysis": selected_stock_analysis,
            "year": year,
            "month": month,
            "start_date": start_date,
            "end_date": end_date,
            "open_date_point": open_date_point,

            # tektura
            "cardboard_stocktype": CARDBOARD_STOCKTYPE,
            "received_material_m2": received_material_m2,
            "received_material_value": received_material_value,
            "processed_material_m2": processed_material_m2,
            "processed_material_value": processed_material_value,

            # magazyny wartości
            "warehouse_values": warehouse_values,
            "total_value_start": total_value_start,
            "total_value_end": total_value_end,
            "total_value_diff": total_value_diff,

            # sprzedaż
            "sales_revenue": sales_revenue,
            "sales_cogs": sales_cogs,
            "sales_profit": sales_profit,
            "profit_per_m2": profit_per_m2,

            # tabela ilości
            "rows": rows,

            # --- kontrole spójności ---
            "sales_fifo_issues": sales_fifo_issues,
            "sales_fifo_issues_count": len(sales_fifo_issues),

            "overused_supplies": sorted(overused_supplies, key=lambda d: (d["name"], d["supply_id"])),
            "overused_supplies_count": len(overused_supplies),

            "missing_dimensions_received_count": missing_dimensions_received_count,
            "missing_dimensions_used_count": missing_dimensions_used_count,
            "missing_dims_received_ids": sorted(set(missing_dims_received))[:200],
            "missing_dims_used_supply_ids": sorted(set(missing_dims_used))[:200],

            "qty_mismatch_rows": qty_mismatch_rows[:200],
            "qty_mismatch_count": len(qty_mismatch_rows),

            # debug flag + tabele debug
            "debug": debug,
            "received_debug_rows": received_debug_rows,
            "used_debug_rows": used_debug_rows,
            "value_start_debug_rows": value_start_debug_rows,
            "value_end_debug_rows": value_end_debug_rows,
        }

        return render(request, self.template_name, context)
