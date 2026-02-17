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


WAREHOUSE_MAIN = "MAGAZYN GŁÓWNY"
WAREHOUSE_FG = "MAGAZYN WYROBÓW GOTOWYCH"

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
) -> tuple[dict[tuple[int, str], Decimal], dict[int, dict]]:
    """
    Wycena stanów na konkretną datę (po partiach StockSupply).
    Zwraca:
      - mapa: (stock_type_id, name) -> remaining_value_at_date
      - debug mapa per supply_id (żeby pokazać jak wyliczyło remaining qty/value)
    """
    if not keys:
        return {}, {}

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
        return {}, {}

    settled_map = {
        row["stock_supply_id"]: int(row["s"] or 0)
        for row in (
            StockSupplySettlement.objects
            .filter(stock_supply_id__in=supply_ids, as_result=False, settlement__settlement_date__lte=date_point)
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

    out: dict[tuple[int, str], Decimal] = {}
    debug_supply: dict[int, dict] = {}

    for s in supplies:
        qty = int(s.quantity or 0)
        if qty <= 0:
            continue

        settled = settled_map.get(s.id, 0)
        sold = sold_map.get(s.id, 0)
        used = settled + sold
        remaining = max(0, qty - used)

        value = Decimal(s.value or 0)
        rem_value = Decimal("0.00")
        if remaining > 0:
            rem_value = (value * Decimal(remaining) / Decimal(qty)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        key = (s.stock_type_id, s.name)
        if remaining > 0:
            out[key] = out.get(key, Decimal("0.00")) + rem_value

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
            "remaining_qty": remaining,
            "remaining_value": rem_value,
            "dimensions": dim,
            "m2_per_unit": dims_to_m2(dim),
        }

    return out, debug_supply


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

        wh_main = Warehouse.objects.get(name=WAREHOUSE_MAIN)
        wh_fg = Warehouse.objects.get(name=WAREHOUSE_FG)

        ws_qs = (
            WarehouseStock.objects
            .select_related("warehouse", "stock", "stock__stock_type")
            .filter(warehouse__in=[wh_main, wh_fg])
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
        for ss in received_supplies:
            dim = supply_effective_dimensions(ss)
            m2_unit = dims_to_m2(dim)
            m2_total = (Decimal(ss.quantity or 0) * m2_unit).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
            received_material_m2 += m2_total

            if debug:
                received_debug_rows.append({
                    "id": ss.id,
                    "date": ss.date,
                    "name": ss.name,
                    "qty": int(ss.quantity or 0),
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
        for row in used_settlements:
            dim = supply_effective_dimensions(row.stock_supply)
            m2_unit = dims_to_m2(dim)
            m2_total = (Decimal(row.quantity or 0) * m2_unit).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
            processed_material_m2 += m2_total

            if debug:
                used_debug_rows.append({
                    "settlement_id": row.settlement_id,
                    "settlement_date": row.settlement.settlement_date if row.settlement_id else None,
                    "supply_id": row.stock_supply_id,
                    "supply_name": row.stock_supply.name if row.stock_supply_id else None,
                    "qty_used": int(row.quantity or 0),
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

        # --- wartość magazynów na daty (po partiach) ---
        keys = {(ws.stock.stock_type_id, ws.stock.name) for ws in ws_qs}
        open_date_point = start_date - datetime.timedelta(days=1)

        value_start_map, value_start_debug = supplies_value_at_date_for_keys(keys, open_date_point)
        value_end_map, value_end_debug = supplies_value_at_date_for_keys(keys, end_date)

        def value_for_warehouse(warehouse_obj: Warehouse, mp: dict[tuple[int, str], Decimal]) -> Decimal:
            total = Decimal("0.00")
            for ws in ws_qs:
                if ws.warehouse_id != warehouse_obj.id:
                    continue
                total += mp.get((ws.stock.stock_type_id, ws.stock.name), Decimal("0.00"))
            return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        main_value_start = value_for_warehouse(wh_main, value_start_map)
        main_value_end = value_for_warehouse(wh_main, value_end_map)
        fg_value_start = value_for_warehouse(wh_fg, value_start_map)
        fg_value_end = value_for_warehouse(wh_fg, value_end_map)

        total_value_start = (main_value_start + fg_value_start).quantize(Decimal("0.01"))
        total_value_end = (main_value_end + fg_value_end).quantize(Decimal("0.01"))

        profit_per_m2 = None
        if processed_material_m2 > 0:
            profit_per_m2 = (sales_profit / processed_material_m2).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

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

        # --- DEBUG: magazyn value w rozbiciu na supply (start/end) ---
        value_start_debug_rows = []
        value_end_debug_rows = []
        if debug:
            # sortujemy, żeby łatwo kontrolować
            value_start_debug_rows = sorted(value_start_debug.values(), key=lambda d: (str(d["date"]), d["name"], d["supply_id"]))
            value_end_debug_rows = sorted(value_end_debug.values(), key=lambda d: (str(d["date"]), d["name"], d["supply_id"]))

        context = {
            "year": year,
            "month": month,
            "start_date": start_date,
            "end_date": end_date,

            "received_material_m2": received_material_m2,
            "received_material_value": received_material_value,
            "processed_material_m2": processed_material_m2,
            "processed_material_value": processed_material_value,

            "main_value_start": main_value_start,
            "main_value_end": main_value_end,
            "fg_value_start": fg_value_start,
            "fg_value_end": fg_value_end,
            "total_value_start": total_value_start,
            "total_value_end": total_value_end,

            "sales_revenue": sales_revenue,
            "sales_cogs": sales_cogs,
            "sales_profit": sales_profit,
            "profit_per_m2": profit_per_m2,

            "rows": rows,

            # debug
            "debug": debug,
            "received_debug_rows": received_debug_rows,
            "used_debug_rows": used_debug_rows,
            "value_start_debug_rows": value_start_debug_rows,
            "value_end_debug_rows": value_end_debug_rows,
            "open_date_point": open_date_point,
            "cardboard_stocktype": CARDBOARD_STOCKTYPE,
        }

        return render(request, self.template_name, context)
