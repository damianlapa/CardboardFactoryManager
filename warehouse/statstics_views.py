import datetime
from django.utils import timezone

from django.http import JsonResponse
from collections import defaultdict
from warehouse.models import Order  # lub zaktualizuj nazwę importu


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

