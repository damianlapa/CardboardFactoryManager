from django.http import JsonResponse
from collections import defaultdict
from warehouse.models import Order  # lub zaktualizuj nazwę importu


def customer_distribution(request):
    try:
        min_percent = float(request.GET.get('min', 0))
        max_percent = float(request.GET.get('max', 100))
    except ValueError:
        min_percent, max_percent = 0, 100

    print(min_percent, max_percent)

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

    return JsonResponse(result, safe=False)
