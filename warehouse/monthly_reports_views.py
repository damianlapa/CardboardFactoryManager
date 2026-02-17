# warehouse/monthly_reports_views.py
import datetime
import calendar
from decimal import Decimal

from django.views import View
from django.shortcuts import render
from django.db.models import OuterRef, Subquery, IntegerField, Sum, F, ExpressionWrapper, DecimalField
from django.db.models.functions import Coalesce

from warehouse.models import (
    Warehouse, WarehouseStock, WarehouseStockHistory,
    OrderSettlement, StockSupplySettlement, ProductSell3
)

WAREHOUSE_MAIN = "MAGAZYN GŁÓWNY"
WAREHOUSE_FG = "MAGAZYN WYROBÓW GOTOWYCH"


def month_range(year: int, month: int):
    start = datetime.date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    end = datetime.date(year, month, last_day)
    return start, end


class MonthlyWarehouseReportView(View):
    template_name = "warehouse/monthly_report.html"

    def _parse_year_month(self, request):
        today = datetime.date.today()
        year = int(request.GET.get("year") or today.year)
        month = int(request.GET.get("month") or today.month)
        month = max(1, min(12, month))
        return year, month

    def get(self, request):
        year, month = self._parse_year_month(request)
        start_date, end_date = month_range(year, month)

        # interesujące magazyny (możesz rozszerzyć)
        wh_main = Warehouse.objects.get(name=WAREHOUSE_MAIN)
        wh_fg = Warehouse.objects.get(name=WAREHOUSE_FG)

        ws_qs = (
            WarehouseStock.objects
            .select_related("warehouse", "stock", "stock__stock_type")
            .filter(warehouse__in=[wh_main, wh_fg])
        )

        # --- SNAPSHOTY z historii ---
        # start_qty: ostatni wpis < start_date
        start_hist = (
            WarehouseStockHistory.objects
            .filter(warehouse_stock=OuterRef("pk"), date__lt=start_date)
            .order_by("-date", "-id")
        )
        # end_qty: ostatni wpis <= end_date
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

        # agregacje per magazyn
        def sum_for_warehouse(qs, warehouse_obj, field):
            return qs.filter(warehouse=warehouse_obj).aggregate(
                s=Coalesce(Sum(field), 0)
            )["s"]

        main_start = sum_for_warehouse(ws_qs, wh_main, "start_qty")
        main_end = sum_for_warehouse(ws_qs, wh_main, "end_qty")
        fg_start = sum_for_warehouse(ws_qs, wh_fg, "start_qty")
        fg_end = sum_for_warehouse(ws_qs, wh_fg, "end_qty")


        # --- PRZETWORZONY MATERIAŁ (ilość) ---
        processed_material_qty = (
            OrderSettlement.objects
            .filter(
                settlement_date__gte=start_date,
                settlement_date__lte=end_date,
                material__warehouse=wh_main,
            )
            .aggregate(s=Coalesce(Sum("material_quantity"), 0))["s"]
        )

        # --- PRZETWORZONY MATERIAŁ (wartość) [opcjonalnie, ale bardzo przydatne] ---
        processed_material_value = (
            StockSupplySettlement.objects
            .filter(
                as_result=False,
                settlement__settlement_date__gte=start_date,
                settlement__settlement_date__lte=end_date,
                settlement__material__warehouse=wh_main,
            )
            .aggregate(s=Coalesce(Sum("value"), Decimal("0.00")))["s"]
        )

        # --- SPRZEDAŻ ---
        sales_qs = ProductSell3.objects.filter(date__gte=start_date, date__lte=end_date)

        # przychód w SQL: sum(price * quantity)
        revenue_expr = ExpressionWrapper(
            F("price") * F("quantity"),
            output_field=DecimalField(max_digits=18, decimal_places=2)
        )
        sales_revenue = sales_qs.aggregate(
            s=Coalesce(Sum(revenue_expr), Decimal("0.00"))
        )["s"]

        # COGS i profit liczymy w Pythonie (pewnie i czytelnie, bo masz StockSupplySell + metody)
        sales = list(sales_qs.select_related("customer", "warehouse_stock", "stock"))
        sales_cogs = sum((s.cogs() for s in sales), Decimal("0.00"))
        sales_profit = (sales_revenue - sales_cogs).quantize(Decimal("0.01"))

        # --- TABELA SZCZEGÓŁOWA (opcjonalna w UI, ale przydatna) ---
        # pokaż tylko pozycje, które miały jakikolwiek ruch/stany
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

        main_diff = main_end - main_start
        fg_diff = fg_end - fg_start
        total_start = main_start + fg_start
        total_end = main_end + fg_end
        total_diff = total_end - total_start

        context = {
            "year": year,
            "month": month,
            "start_date": start_date,
            "end_date": end_date,

            "main_start": main_start,
            "main_end": main_end,
            "fg_start": fg_start,
            "fg_end": fg_end,

            "processed_material_qty": processed_material_qty,
            "processed_material_value": processed_material_value,

            "sales_revenue": sales_revenue,
            "sales_cogs": sales_cogs,
            "sales_profit": sales_profit,

            "rows": rows,

            "main_diff": main_diff,
            "fg_diff": fg_diff,
            "total_start": total_start,
            "total_end": total_end,
            "total_diff": total_diff,
        }
        return render(request, self.template_name, context)
