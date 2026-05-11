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
            value = Decimal(warehouse.count_warehouse_value() or 0)
            total_warehouse_value += value

            warehouse_cards.append({
                "warehouse": warehouse,
                "value": value,
                "stocks_count": WarehouseStock.objects.filter(
                    warehouse=warehouse,
                    quantity__gt=0
                ).count(),
            })

        month_sales = ProductSell3.objects.filter(
            date__gte=month_start,
            date__lte=today
        ).select_related("customer", "product", "stock")

        sales_value = Decimal("0.00")
        sales_profit = Decimal("0.00")

        for sell in month_sales:
            sales_value += sell.revenue()
            sales_profit += sell.profit()

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

            "sales_value": sales_value,
            "sales_profit": sales_profit,
            "month_sales_count": month_sales.count(),

            "latest_sales": latest_sales,
            "latest_deliveries": latest_deliveries,
            "unsettled_orders": unsettled_orders,
            "zero_stocks": zero_stocks,
        }

        return render(request, self.template_name, context)
