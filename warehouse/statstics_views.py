# warehouse/statistic_views.py

import datetime
from django.utils import timezone

from django.http import JsonResponse
from collections import defaultdict
from warehouse.models import *

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Sum
from django.utils import timezone
from decimal import Decimal
import datetime

from django.urls import reverse_lazy
from django.views import View
from django.shortcuts import render

from decimal import Decimal
import json


def customer_distribution(request):
    try:
        min_percent = float(request.GET.get('min', 0))
        max_percent = float(request.GET.get('max', 100))
    except ValueError:
        min_percent, max_percent = 0, 100

    orders = Order.objects.select_related('customer')
    area_by_customer = defaultdict(float)
    total_area = 0.0

    for order in orders:
        area = order.total_area()
        customer = str(order.customer)
        area_by_customer[customer] += area
        total_area += area

    result = []
    for customer, area in area_by_customer.items():
        percent = (area / total_area) * 100 if total_area > 0 else 0
        if min_percent <= percent <= max_percent:
            result.append({
                'customer': customer,
                'surface_area': round(area, 2),
                'percentage': round(percent, 2)
            })

    result = sorted(result, key=lambda x: x['percentage'], reverse=True)

    return JsonResponse(result, safe=False)


def customer_orders(request):
    user = request.user

    if user.has_perm('warehouse.add_month_result'):

        today = timezone.now().date()

        try:
            min_days = int(request.GET.get('min', 0))
            max_days = int(request.GET.get('max', 365))
        except ValueError:
            min_days, max_days = 0, 365

        # Pobierz wszystkie zamówienia np. z ostatnich 2 lat (lub bez ograniczenia)
        orders = Order.objects.select_related('customer').filter(
            order_date__gte=today - datetime.timedelta(days=730)
        )

        last_orders = {}

        for order in orders:
            customer = str(order.customer)
            order_date = order.order_date

            if customer not in last_orders or order_date > last_orders[customer]:
                last_orders[customer] = order_date

        result = []
        for customer, last_date in last_orders.items():
            days_since = (today - last_date).days
            if min_days <= days_since <= max_days:
                result.append({
                    'customer': customer,
                    'days_since_last': days_since
                })

        # Posortuj od najstarszej do najnowszej dostawy (opcjonalnie)
        result.sort(key=lambda x: x['days_since_last'], reverse=True)

        return JsonResponse(result, safe=False)



class WarehouseDashboardView(LoginRequiredMixin, View):
    login_url = reverse_lazy('login')
    template_name = "warehouse/dashboard.html"

    def get(self, request):
        today = datetime.datetime.now().date()
        month_start = today.replace(day=1)

        active_orders = Order.objects.filter(delivered=True, finished=False).count()
        open_orders = Order.objects.filter(finished=False).count()

        unprocessed_deliveries = Delivery.objects.filter(processed=False).count()
        unprocessed_special_deliveries = DeliverySpecial.objects.filter(processed=False).count()

        warehouse_stocks_count = WarehouseStock.objects.filter(quantity__gt=0).count()
        bom_count = BOM.objects.count()

        warehouses = Warehouse.objects.all()
        warehouse_cards = []
        total_warehouse_value = Decimal("0.00")

        for warehouse in warehouses:
            value = Decimal(warehouse.value or 0)
            total_warehouse_value += value

            warehouse_cards.append({
                "warehouse": warehouse,
                "value": value,
                "stocks_count": WarehouseStock.objects.filter(
                    warehouse=warehouse,
                    quantity__gt=0
                ).count(),
            })

        warehouse_labels = []
        warehouse_values = []

        for item in warehouse_cards:
            warehouse_labels.append(str(item["warehouse"].name))
            warehouse_values.append(float(item["value"] or 0))

        for item in warehouse_cards:
            if total_warehouse_value > 0:
                item["percent"] = round(
                    Decimal(item["value"]) / Decimal(total_warehouse_value) * Decimal("100"),
                    1
                )
            else:
                item["percent"] = Decimal("0.0")

        month_sales = ProductSell3.objects.filter(
            date__gte=month_start,
            date__lte=today
        ).select_related("customer", "product", "stock")

        sales_value = Decimal("0.00")
        sales_profit = Decimal("0.00")

        for sell in month_sales:
            sales_value += sell.revenue()
            sales_profit += sell.profit()

        month_sales_count = month_sales.count()

        latest_sales = month_sales.order_by("-date")[:8]

        latest_deliveries = Delivery.objects.select_related(
            "provider"
        ).order_by("-date", "-id")[:8]

        unsettled_orders = Order.objects.filter(
            delivered=True,
            finished=False
        ).select_related("customer", "provider").order_by("-delivery_date")[:8]

        zero_stocks = WarehouseStock.objects.filter(
            quantity=0
        ).select_related("warehouse", "stock")[:8]

        # === CHARTS: ostatnie 30 dni sprzedaży i zysku ===
        chart_days = []
        sales_by_day = []
        profit_by_day = []

        date_from = today - datetime.timedelta(days=29)

        sales_map = defaultdict(lambda: {
            "revenue": Decimal("0.00"),
            "profit": Decimal("0.00"),
        })

        sales_30_days = ProductSell3.objects.filter(
            date__gte=date_from,
            date__lte=today
        ).select_related("customer", "product", "stock")

        for sell in sales_30_days:
            sales_map[sell.date]["revenue"] += sell.revenue()
            sales_map[sell.date]["profit"] += sell.profit()

        for i in range(30):
            day = date_from + datetime.timedelta(days=i)
            chart_days.append(day.strftime("%d.%m"))
            sales_by_day.append(float(sales_map[day]["revenue"]))
            profit_by_day.append(float(sales_map[day]["profit"]))

        # === CHARTS: wartość magazynów ===
        warehouse_labels = []
        warehouse_values = []

        for item in warehouse_cards:
            warehouse_labels.append(str(item["warehouse"].name))
            warehouse_values.append(float(item["value"]))

        warehouse_labels_json = json.dumps(warehouse_labels)
        warehouse_values_json = json.dumps(warehouse_values)
        chart_days_json = json.dumps(chart_days)
        sales_by_day_json = json.dumps(sales_by_day)
        profit_by_day_json = json.dumps(profit_by_day)

        # === ALERTY / CENTRUM KONTROLI ===

        dashboard_alerts = []

        if unprocessed_deliveries > 0:
            dashboard_alerts.append({
                "level": "warning",
                "title": "Dostawy do przyjęcia",
                "message": f"{unprocessed_deliveries} dostaw czeka na przetworzenie.",
                "url": "warehouse:delivery_list",
            })

        if unprocessed_special_deliveries > 0:
            dashboard_alerts.append({
                "level": "warning",
                "title": "Dostawy specjalne",
                "message": f"{unprocessed_special_deliveries} dostaw specjalnych czeka na przetworzenie.",
                "url": None,
            })

        unsettled_orders_count = Order.objects.filter(
            delivered=True,
            finished=False
        ).count()

        if unsettled_orders_count > 0:
            dashboard_alerts.append({
                "level": "danger",
                "title": "Zlecenia dostarczone, ale otwarte",
                "message": f"{unsettled_orders_count} zleceń wymaga rozliczenia lub zamknięcia.",
                "url": "warehouse:order_list",
            })

        zero_stocks_count = WarehouseStock.objects.filter(quantity=0).count()

        if zero_stocks_count > 0:
            dashboard_alerts.append({
                "level": "info",
                "title": "Stany zerowe",
                "message": f"{zero_stocks_count} pozycji magazynowych ma stan 0.",
                "url": "warehouse:warehouse-list-view",
            })

        products_without_price_count = Product.objects.filter(price=0).count()

        if products_without_price_count > 0:
            dashboard_alerts.append({
                "level": "warning",
                "title": "Produkty bez ceny",
                "message": f"{products_without_price_count} produktów ma cenę 0.",
                "url": None,
            })

        bom_without_parts_count = BOM.objects.filter(parts__isnull=True).distinct().count()

        if bom_without_parts_count > 0:
            dashboard_alerts.append({
                "level": "danger",
                "title": "BOM bez części",
                "message": f"{bom_without_parts_count} BOM nie ma dodanych części.",
                "url": "warehouse:bom_list",
            })

        negative_sales = []

        for sell in ProductSell3.objects.filter(
            date__gte=month_start,
            date__lte=today
        ).select_related("customer", "product", "stock")[:100]:
            try:
                if sell.profit() < 0:
                    negative_sales.append(sell)
            except Exception:
                pass

        if negative_sales:
            dashboard_alerts.append({
                "level": "danger",
                "title": "Sprzedaże ze stratą",
                "message": f"{len(negative_sales)} sprzedaży w tym miesiącu ma ujemny wynik.",
                "url": "warehouse:sells-list-view",
            })

        # === RAPORTY / SZYBKA ANALIZA ===

        reports = [
            {
                "title": "Rentowność zleceń",
                "description": "Koszt, sprzedaż i wynik na zleceniach.",
                "value": unsettled_orders_count,
                "value_label": "otwartych po dostawie",
                "url": "warehouse:orders-profitability",
                "level": "primary",
            },
            {
                "title": "Statystyki dostaw",
                "description": "Dostawy według okresów i dostawców.",
                "value": unprocessed_deliveries,
                "value_label": "do przyjęcia",
                "url": "warehouse:deliveries-statistics",
                "level": "warning",
            },
            {
                "title": "Raport miesięczny",
                "description": "Podsumowanie sprzedaży i magazynu.",
                "value": f"{sales_profit:.2f} zł",
                "value_label": "wynik miesiąca",
                "url": "warehouse:monthly_report",
                "level": "success" if sales_profit >= 0 else "danger",
            },
            {
                "title": "Cenniki",
                "description": "Upload i aktualizacja cenników.",
                "value": products_without_price_count,
                "value_label": "produktów bez ceny",
                "url": "warehouse:price_list-upload",
                "level": "secondary",
            },
        ]

        # === TOP LISTY ===

        sales_month_qs = ProductSell3.objects.filter(
            date__gte=month_start,
            date__lte=today
        ).select_related("customer", "product", "stock")

        top_customers_map = defaultdict(Decimal)
        top_products_map = defaultdict(Decimal)
        top_negative_sales = []

        for sell in sales_month_qs:
            customer_name = str(sell.customer) if sell.customer else (sell.customer_alter_name or "Brak klienta")

            if sell.product:
                product_name = sell.product.name
            elif sell.stock:
                product_name = sell.stock.name
            else:
                product_name = "Brak produktu"

            revenue = sell.revenue()
            profit = sell.profit()

            top_customers_map[customer_name] += revenue
            top_products_map[product_name] += revenue

            if profit < 0:
                top_negative_sales.append({
                    "sell": sell,
                    "name": product_name,
                    "customer": customer_name,
                    "profit": profit,
                    "revenue": revenue,
                })

        top_customers = sorted(
            top_customers_map.items(),
            key=lambda x: x[1],
            reverse=True
        )[:8]

        top_products = sorted(
            top_products_map.items(),
            key=lambda x: x[1],
            reverse=True
        )[:8]

        top_negative_sales = sorted(
            top_negative_sales,
            key=lambda x: x["profit"]
        )[:8]

        # === SZYBKIE AKCJE Z LICZNIKAMI ===

        quick_actions = [
            {
                "title": "Zlecenia",
                "description": "Lista aktywnych i dostarczonych zleceń.",
                "count": active_orders,
                "url": "warehouse:order_list",
                "badge": "primary",
            },
            {
                "title": "Dodaj zamówienie",
                "description": "Ręczne dodanie lub import zamówienia.",
                "count": "+",
                "url": "warehouse:add-orders",
                "badge": "success",
            },
            {
                "title": "Dostawy",
                "description": "Przyjęcia materiałów i dostaw specjalnych.",
                "count": unprocessed_deliveries,
                "url": "warehouse:delivery_list",
                "badge": "warning",
            },
            {
                "title": "Sprzedaż",
                "description": "Lista sprzedaży i rozchody FIFO.",
                "count": month_sales_count,
                "url": "warehouse:sells-list-view",
                "badge": "success",
            },
            {
                "title": "Magazyny",
                "description": "Stany, wartości i historia ruchów.",
                "count": warehouse_stocks_count,
                "url": "warehouse:warehouse-list-view",
                "badge": "secondary",
            },
            {
                "title": "Cennik",
                "description": "Upload i aktualizacja cenników.",
                "count": products_without_price_count,
                "url": "warehouse:price_list-upload",
                "badge": "dark",
            },
        ]

        # === STATUS SYSTEMU ===

        system_status = []

        system_status.append({
            "title": "Magazyn",
            "status": "OK" if zero_stocks_count == 0 else "UWAGA",
            "description": "Stany magazynowe i dostępność pozycji.",
            "value": zero_stocks_count,
            "label": "stanów zerowych",
            "level": "success" if zero_stocks_count == 0 else "warning",
        })

        system_status.append({
            "title": "Dostawy",
            "status": "OK" if unprocessed_deliveries == 0 else "UWAGA",
            "description": "Dostawy oczekujące na przyjęcie.",
            "value": unprocessed_deliveries,
            "label": "do przyjęcia",
            "level": "success" if unprocessed_deliveries == 0 else "warning",
        })

        system_status.append({
            "title": "Zlecenia",
            "status": "OK" if unsettled_orders_count == 0 else "PILNE",
            "description": "Zlecenia dostarczone, ale nadal otwarte.",
            "value": unsettled_orders_count,
            "label": "otwartych po dostawie",
            "level": "success" if unsettled_orders_count == 0 else "danger",
        })

        system_status.append({
            "title": "Cenniki",
            "status": "OK" if products_without_price_count == 0 else "UWAGA",
            "description": "Produkty bez ustawionej ceny.",
            "value": products_without_price_count,
            "label": "bez ceny",
            "level": "success" if products_without_price_count == 0 else "warning",
        })

        system_status.append({
            "title": "BOM",
            "status": "OK" if bom_without_parts_count == 0 else "PILNE",
            "description": "Receptury bez dodanych części.",
            "value": bom_without_parts_count,
            "label": "BOM bez części",
            "level": "success" if bom_without_parts_count == 0 else "danger",
        })

        # === OSTATNIE RUCHY MAGAZYNOWE ===

        # === OSTATNIE RUCHY MAGAZYNOWE ===

        latest_stock_moves_raw = (
            WarehouseStockHistory.objects
            .select_related(
                "warehouse_stock",
                "warehouse_stock__warehouse",
                "warehouse_stock__stock",
                "stock_supply",
                "order_settlement",
                "order_settlement__order",
                "sell",
                "assembly",
            )
            .order_by("-date", "-id")[:12]
        )

        latest_stock_moves = []

        for move in latest_stock_moves_raw:

            quantity_before = move.quantity_before or 0
            quantity_after = move.quantity_after or 0

            delta = quantity_after - quantity_before

            if delta > 0:
                move_type = "in"
            elif delta < 0:
                move_type = "out"
            else:
                move_type = "neutral"

            # źródło ruchu
            if move.sell:
                source_label = "Sprzedaż"
                source_badge = "danger"

            elif move.stock_supply:
                source_label = "Przyjęcie"
                source_badge = "success"

            elif move.order_settlement:
                source_label = "Produkcja"
                source_badge = "warning"

            elif move.assembly:
                source_label = "Montaż"
                source_badge = "info"

            else:
                source_label = "Ruch"
                source_badge = "secondary"

            latest_stock_moves.append({
                "move": move,
                "delta": delta,
                "type": move_type,
                "source_label": source_label,
                "source_badge": source_badge,
            })

        # === OPERACJE: DZIŚ / 7 DNI / 30 DNI ===

        def build_period_summary(label, date_from, date_to):
            sales_qs = ProductSell3.objects.filter(
                date__gte=date_from,
                date__lte=date_to
            )

            sales_value = Decimal("0.00")
            sales_profit = Decimal("0.00")

            for sell in sales_qs:
                try:
                    sales_value += sell.revenue()
                    sales_profit += sell.profit()
                except Exception:
                    pass

            deliveries_count = Delivery.objects.filter(
                date__gte=date_from,
                date__lte=date_to
            ).count()

            stock_moves_count = WarehouseStockHistory.objects.filter(
                date__gte=date_from,
                date__lte=date_to
            ).count()

            return {
                "label": label,
                "date_from": date_from,
                "date_to": date_to,
                "items": [
                    {
                        "title": "Sprzedaż",
                        "value": f"{sales_value:.2f} zł",
                        "description": f"{sales_qs.count()} pozycji sprzedaży",
                        "level": "success",
                    },
                    {
                        "title": "Wynik",
                        "value": f"{sales_profit:.2f} zł",
                        "description": "Przychód minus koszt FIFO",
                        "level": "success" if sales_profit >= 0 else "danger",
                    },
                    {
                        "title": "Dostawy",
                        "value": deliveries_count,
                        "description": "Dostawy w okresie",
                        "level": "primary",
                    },
                    {
                        "title": "Ruchy magazynowe",
                        "value": stock_moves_count,
                        "description": "Operacje magazynowe",
                        "level": "secondary",
                    },
                ]
            }

        operations_periods = [
            build_period_summary(
                "Dzisiaj",
                today,
                today
            ),
            build_period_summary(
                "Ostatnie 7 dni",
                today - datetime.timedelta(days=6),
                today
            ),
            build_period_summary(
                "Ostatnie 30 dni",
                today - datetime.timedelta(days=29),
                today
            ),
        ]

        # === KOLEJKA PRACY / TODO ===

        work_queue = []

        if unprocessed_deliveries > 0:
            work_queue.append({
                "title": "Przyjmij dostawy",
                "description": f"{unprocessed_deliveries} dostaw czeka na przetworzenie.",
                "priority": "Wysoki",
                "level": "warning",
                "url": "warehouse:delivery_list",
            })

        if unsettled_orders_count > 0:
            work_queue.append({
                "title": "Rozlicz zlecenia",
                "description": f"{unsettled_orders_count} zleceń jest dostarczonych, ale nadal otwartych.",
                "priority": "Pilne",
                "level": "danger",
                "url": "warehouse:order_list",
            })

        if products_without_price_count > 0:
            work_queue.append({
                "title": "Uzupełnij ceny produktów",
                "description": f"{products_without_price_count} produktów ma cenę 0.",
                "priority": "Średni",
                "level": "warning",
                "url": "warehouse:price_list-upload",
            })

        if bom_without_parts_count > 0:
            work_queue.append({
                "title": "Popraw BOM",
                "description": f"{bom_without_parts_count} BOM nie ma dodanych części.",
                "priority": "Pilne",
                "level": "danger",
                "url": "warehouse:bom_list",
            })

        if negative_sales:
            work_queue.append({
                "title": "Sprawdź sprzedaże ze stratą",
                "description": f"{len(negative_sales)} sprzedaży w tym miesiącu ma ujemny wynik.",
                "priority": "Wysoki",
                "level": "danger",
                "url": "warehouse:sells-list-view",
            })

        if not work_queue:
            work_queue.append({
                "title": "Brak pilnych zadań",
                "description": "System nie wykrył krytycznych tematów do obsługi.",
                "priority": "OK",
                "level": "success",
                "url": None,
            })

        # === TOP PROBLEMY / ANALIZA MAGAZYNU ===

        zero_stock_items = (
            WarehouseStock.objects
            .filter(quantity=0)
            .select_related("warehouse", "stock")
            .order_by("warehouse__name", "stock__name")[:10]
        )

        top_warehouse_values = []

        warehouse_stocks_for_value = (
            WarehouseStock.objects
            .filter(quantity__gt=0)
            .select_related("warehouse", "stock", "stock__stock_type")[:200]
        )

        for ws in warehouse_stocks_for_value:
            try:
                value = Decimal(ws.count_value() or 0)
            except Exception:
                value = Decimal("0.00")

            if value > 0:
                top_warehouse_values.append({
                    "ws": ws,
                    "value": value,
                })

        top_warehouse_values = sorted(
            top_warehouse_values,
            key=lambda x: x["value"],
            reverse=True
        )[:10]

        latest_stock_history_ids = (
            WarehouseStockHistory.objects
            .values_list("warehouse_stock_id", flat=True)
            .distinct()
        )

        stocks_without_recent_moves = (
            WarehouseStock.objects
            .filter(quantity__gt=0)
            .exclude(id__in=latest_stock_history_ids)
            .select_related("warehouse", "stock")
            .order_by("warehouse__name", "stock__name")[:10]
        )

        context = {
            "today": today,
            "month_start": month_start,

            "active_orders": active_orders,
            "open_orders": open_orders,
            "unprocessed_deliveries": unprocessed_deliveries,
            "unprocessed_special_deliveries": unprocessed_special_deliveries,
            "warehouse_stocks_count": warehouse_stocks_count,
            "bom_count": bom_count,

            "warehouses": warehouse_cards,
            "total_warehouse_value": total_warehouse_value,
            "warehouse_labels": warehouse_labels,
            "warehouse_values": warehouse_values,
            "chart_days_json": chart_days_json,
            "sales_by_day_json": sales_by_day_json,
            "profit_by_day_json": profit_by_day_json,
            "warehouse_labels_json": warehouse_labels_json,
            "warehouse_values_json": warehouse_values_json,

            "sales_value": sales_value,
            "sales_profit": sales_profit,
            "month_sales_count": month_sales.count(),

            "latest_sales": latest_sales,
            "latest_deliveries": latest_deliveries,
            "unsettled_orders": unsettled_orders,
            "zero_stocks": zero_stocks,

            "chart_days": chart_days,
            "sales_by_day": sales_by_day,
            "profit_by_day": profit_by_day,

            "dashboard_alerts": dashboard_alerts,
            "unsettled_orders_count": unsettled_orders_count,
            "zero_stocks_count": zero_stocks_count,
            "products_without_price_count": products_without_price_count,
            "bom_without_parts_count": bom_without_parts_count,
            "negative_sales": negative_sales[:8],

            "reports": reports,

            "top_customers": top_customers,
            "top_products": top_products,
            "top_negative_sales": top_negative_sales,

            "quick_actions": quick_actions,

            "system_status": system_status,

            "latest_stock_moves": latest_stock_moves,

            "operations_periods": operations_periods,

            "work_queue": work_queue,

            "zero_stock_items": zero_stock_items,
            "top_warehouse_values": top_warehouse_values,
            "stocks_without_recent_moves": stocks_without_recent_moves,
        }

        return render(request, self.template_name, context)


class DashboardDataView(LoginRequiredMixin, View):
    login_url = reverse_lazy('login')

    def get(self, request):

        today = datetime.datetime.now().date()
        month_start = today.replace(day=1)

        active_orders = Order.objects.filter(
            delivered=True,
            finished=False
        ).count()

        unprocessed_deliveries = Delivery.objects.filter(
            processed=False
        ).count()

        warehouse_value = Decimal("0.00")

        for warehouse in Warehouse.objects.all():
            warehouse_value += Decimal(
                warehouse.count_warehouse_value() or 0
            )

        month_sales = ProductSell3.objects.filter(
            date__gte=month_start,
            date__lte=today
        )

        sales_value = Decimal("0.00")
        sales_profit = Decimal("0.00")

        for sell in month_sales:
            try:
                sales_value += sell.revenue()
                sales_profit += sell.profit()
            except Exception:
                pass

        latest_sales = []

        sells = ProductSell3.objects.select_related(
            "customer",
            "product",
            "stock"
        ).order_by("-date")[:5]

        for sell in sells:

            if sell.product:
                product_name = sell.product.name
            elif sell.stock:
                product_name = sell.stock.name
            else:
                product_name = "-"

            latest_sales.append({
                "date": sell.date.strftime("%d.%m.%Y"),
                "product": product_name,
                "customer": str(sell.customer) if sell.customer else (
                    sell.customer_alter_name or "-"
                ),
                "value": float(sell.revenue())
            })

        data = {
            "active_orders": active_orders,
            "unprocessed_deliveries": unprocessed_deliveries,
            "warehouse_value": float(warehouse_value),
            "sales_value": float(sales_value),
            "sales_profit": float(sales_profit),
            "latest_sales": latest_sales,
        }

        return JsonResponse(data)