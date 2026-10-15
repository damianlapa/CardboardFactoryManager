"""warehouse/lead_time.py - production order lead-time report."""
from bisect import bisect_left, bisect_right
from collections import defaultdict
from datetime import date, datetime, timedelta
from statistics import mean, median

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Max, Q, F
from django.shortcuts import render
from django.utils import timezone
from django.utils.dateparse import parse_date

from production.models import ProductionOrder
from warehouse.models import Order
from warehousemanager.models import Buyer, Holiday

METRICS = {
    'total': ('Całkowity czas realizacji', 'customer_date', 'production_end'),
    'ordering': ('Złożenie zamówienia surowca', 'customer_date', 'order_date'),
    'delivery': ('Oczekiwanie na dostawę surowca', 'order_date', 'delivery_date'),
    'after_delivery': ('Od dostawy do końca produkcji', 'delivery_date', 'production_end'),
    'after_order': ('Od zamówienia surowca do końca produkcji', 'order_date', 'production_end'),
}


def _as_date(value):
    if isinstance(value, datetime):
        if timezone.is_aware(value):
            return timezone.localtime(value).date()
        return value.date()
    return value if isinstance(value, date) else None


def _business_days(start, end, holidays):
    """Working days in (start, end], i.e. same date => 0."""
    if end < start:
        return None
    begin = start + timedelta(days=1)
    if begin > end:
        return 0
    span = (end - begin).days + 1
    full_weeks, remainder = divmod(span, 7)
    result = full_weeks * 5 + sum((begin + timedelta(days=i)).weekday() < 5 for i in range(remainder))
    left = bisect_left(holidays, begin)
    right = bisect_right(holidays, end)
    return result - (right - left)


def _period_start(day, grouping):
    if grouping == 'week':
        return day - timedelta(days=day.weekday())
    return day.replace(day=1)


def _period_label(day, grouping):
    if grouping == 'week':
        iso = day.isocalendar()
        return f'{iso.year}-W{iso.week:02d}'
    return day.strftime('%Y-%m')


@login_required
def lead_time_report(request):
    today = datetime.today().date()
    default_from = (today.replace(day=1) - timedelta(days=365)).replace(day=1)

    metric = request.GET.get('metric', 'total')
    if metric not in METRICS:
        metric = 'total'
    grouping = request.GET.get('grouping', 'month')
    if grouping not in ('week', 'month'):
        grouping = 'month'

    date_from = parse_date(request.GET.get('date_from', '')) or default_from
    date_to = parse_date(request.GET.get('date_to', '')) or today
    if date_from > date_to:
        date_from, date_to = date_to, date_from

    customer_id = request.GET.get('customer', '')
    if not customer_id.isdigit():
        customer_id = ''

    # ProductionOrder has no FK to warehouse.Order. Match using existing id_number convention.
    # Keep only orders with all units finished AND dated.
    production_qs = (
        ProductionOrder.objects
        .annotate(
            unit_count=Count('productionunit', distinct=True),
            finished_count=Count('productionunit', filter=Q(
                productionunit__status='FINISHED',
                productionunit__end__isnull=False,
            ), distinct=True),
            production_end=Max('productionunit__end', filter=Q(
                productionunit__status='FINISHED',
                productionunit__end__isnull=False,
            )),
        )
        .filter(unit_count__gt=0, unit_count=F('finished_count'))
        .values_list('id_number', 'production_end')
    )
    production_ends = {key: _as_date(end) for key, end in production_qs}

    orders = Order.objects.select_related('provider', 'customer').all()
    if customer_id:
        orders = orders.filter(customer_id=int(customer_id))

    _, start_field, end_field = METRICS[metric]
    # Get candidate pairs first; holiday lookup covers the whole actual date span.
    candidates = []
    for order in orders.iterator(chunk_size=1000):
        end_production = production_ends.get(f'{order.provider} {order.order_id}')
        values = {
            'customer_date': order.customer_date,
            'order_date': order.order_date,
            'delivery_date': order.delivery_date,
            'production_end': end_production,
        }
        start = _as_date(values[start_field])
        end = _as_date(values[end_field])
        if not start or not end or end < start or not date_from <= end <= date_to:
            continue
        candidates.append((order, start, end))

    holiday_dates = []
    if candidates:
        earliest = min(start for _, start, _ in candidates)
        latest = max(end for _, _, end in candidates)
        holiday_dates = sorted({d for d in Holiday.objects.filter(
            holiday_date__gte=earliest, holiday_date__lte=latest
        ).values_list('holiday_date', flat=True) if d.weekday() < 5})

    by_period = defaultdict(list)
    details = []
    for order, start, end in candidates:
        days = _business_days(start, end, holiday_dates)
        period = _period_start(end, grouping)
        by_period[period].append(days)
        details.append({
            'order': order, 'start': start, 'end': end, 'days': days,
            'period': _period_label(period, grouping),
        })

    details.sort(key=lambda item: (item['end'], item['order'].pk), reverse=True)
    periods = [
        {
            'label': _period_label(period, grouping),
            'average': round(mean(values), 2),
            'median': round(median(values), 2),
            'count': len(values),
        }
        for period, values in sorted(by_period.items())
    ]
    all_values = [row['days'] for row in details]

    return render(request, 'warehouse/lead_time_report.html', {
        'metric': metric, 'grouping': grouping,
        'metrics': METRICS, 'metric_title': METRICS[metric][0],
        'date_from': date_from.isoformat(), 'date_to': date_to.isoformat(),
        'customer_id': customer_id,
        'customers': Buyer.objects.order_by('name') if hasattr(Buyer, 'name') else Buyer.objects.order_by('pk'),
        'periods': periods, 'details': details,
        'average': round(mean(all_values), 2) if all_values else None,
        'median': round(median(all_values), 2) if all_values else None,
        'count': len(all_values),
        'chart_labels': [p['label'] for p in periods],
        'chart_values': [p['average'] for p in periods],
    })
