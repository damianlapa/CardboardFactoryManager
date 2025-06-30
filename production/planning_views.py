from django.views.generic import DetailView, View, ListView, CreateView
from django.shortcuts import redirect, get_object_or_404
from production.models import WeeklyPlan, ProductionOrder, ProductionUnit, WorkStation
from production.planning import generate_provisional_plan
from production.forms import QuickProductionUnitForm
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
from django.http import JsonResponse
import json
from django.views.decorators.csrf import csrf_exempt
from django.db.models import F, Max
from django.db.models import Q
import re
from .models import PRODUCTION_ORDER_STATUSES


def parse_dimensions(dim_str):
    try:
        return list(map(int, re.findall(r'\d+', dim_str)))
    except:
        return []


def find_similar_orders(order):
    base_dims = parse_dimensions(order.dimensions)
    if len(base_dims) != 3:
        return []

    tolerance = 0.2

    min_d = [int(d * (1 - tolerance)) for d in base_dims]
    max_d = [int(d * (1 + tolerance)) for d in base_dims]

    candidates = ProductionOrder.objects.exclude(id=order.id).filter(
        dimensions__regex=r'^\d+x\d+x\d+$',
    )

    similar = []

    for o in candidates:
        dims = parse_dimensions(o.dimensions)
        if len(dims) != 3:
            continue

        if not all(mn <= val <= mx for val, mn, mx in zip(dims, min_d, max_d)):
            continue

        try:
            diffs = [abs(base - comp) / base for base, comp in zip(base_dims, dims)]
            score = sum(diffs)
            if order.quantity:
                quantity_difference = abs(order.quantity - o.quantity)/order.quantity
            else:
                quantity_difference = 1

            if quantity_difference >= 1:
                quantity_difference = 1

            score += quantity_difference

            similar.append((score, o))
        except ZeroDivisionError:
            continue

    similar.sort(key=lambda x: x[0])
    return [o for _, o in similar[:30]]


@csrf_exempt
@require_POST
def reorder_units(request, order_id):
    data = json.loads(request.body)
    unit_ids = data.get('unit_ids', [])

    for index, unit_id in enumerate(unit_ids, start=1):
        ProductionUnit.objects.filter(id=unit_id, production_order_id=order_id).update(sequence=index)

    order = get_object_or_404(ProductionOrder, id=order_id)
    html = render_to_string("production/_order_detail_fragment.html", {
        "selected_order": order,
        "units": order.productionunit_set.order_by('sequence').select_related('work_station'),
        "work_stations": WorkStation.objects.all(),
    }, request=request)

    return JsonResponse({"html": html})


@require_POST
def ajax_update_unit(request, unit_id):
    unit = get_object_or_404(ProductionUnit, id=unit_id)

    unit.work_station_id = request.POST.get('work_station')
    unit.estimated_time = request.POST.get('estimated_time')
    unit.required_operators = request.POST.get('required_operators')
    unit.required_helpers = request.POST.get('required_helpers')
    unit.save()

    order = unit.production_order

    html = render_to_string("production/_order_detail_fragment.html", {
        "selected_order": order,
        "units": order.productionunit_set.select_related('work_station'),
        "work_stations": WorkStation.objects.all(),
    }, request=request)

    return JsonResponse({"html": html})


@require_POST
def ajax_delete_unit(request, unit_id):
    unit = get_object_or_404(ProductionUnit, id=unit_id)
    order = unit.production_order
    removed_seq = unit.sequence
    unit.delete()

    # Zmniejsz sequence pozostałym
    ProductionUnit.objects.filter(production_order=order, sequence__gt=removed_seq).update(sequence=F('sequence') - 1)

    html = render_to_string("production/_order_detail_fragment.html", {
        "selected_order": order,
        "units": order.productionunit_set.order_by('sequence').select_related('work_station'),
        "work_stations": WorkStation.objects.all(),
    }, request=request)

    return JsonResponse({"html": html})


@require_POST
def ajax_add_unit(request, order_id):
    order = get_object_or_404(ProductionOrder, id=order_id)

    max_sequence = ProductionUnit.objects.filter(production_order=order).aggregate(Max('sequence'))['sequence__max'] or 0

    unit = ProductionUnit.objects.create(
        production_order=order,
        sequence=max_sequence + 1,
        work_station_id=request.POST.get('work_station'),
        estimated_time=request.POST.get('estimated_time'),
        required_operators=request.POST.get('required_operators'),
        required_helpers=request.POST.get('required_helpers'),
    )

    html = render_to_string("production/_order_detail_fragment.html", {
        "selected_order": order,
        "units": order.productionunit_set.order_by('sequence').select_related('work_station'),
        "work_stations": WorkStation.objects.all(),
    }, request=request)

    return JsonResponse({"html": html})


def ajax_order_detail(request, order_id):
    order = get_object_or_404(ProductionOrder, id=order_id)
    workstations = WorkStation.objects.all()
    units = order.productionunit_set.select_related('work_station').all()
    similar_orders = find_similar_orders(order)

    center_html = render_to_string("production/_order_detail_fragment.html", {
        "selected_order": order,
        "units": units,
        "work_stations": workstations,
        "PRODUCTION_ORDER_STATUSES": PRODUCTION_ORDER_STATUSES
    }, request=request)

    right_html = render_to_string("production/_similar_orders_fragment.html", {
        "similar_orders": similar_orders
    }, request=request)

    return JsonResponse({
        "center_html": center_html,
        "right_html": right_html
    })


@require_POST
def ajax_update_order_status(request, order_id):
    status = request.POST.get('status')
    order = get_object_or_404(ProductionOrder, id=order_id)

    if status in dict(PRODUCTION_ORDER_STATUSES):
        order.status = status
        order.save()

    return ajax_order_detail(request, order.id)


class WeeklyPlanDetailView(DetailView):
    model = WeeklyPlan
    template_name = 'production/weekly_plan_detail.html'
    context_object_name = 'plan'

    def get_object(self, queryset=None):
        year = self.kwargs.get('year')
        week = self.kwargs.get('week')
        plan, _ = WeeklyPlan.objects.get_or_create(year=year, week=week)
        return plan


class WeeklyPlanGenerateView(View):
    def post(self, request, year, week):
        generate_provisional_plan(year, week)
        return redirect('weekly_plan_detail', year=year, week=week)


class IncompleteOrdersView(ListView):
    model = ProductionOrder
    template_name = 'production/uncompleted_orders.html'
    context_object_name = 'orders'

    def get_queryset(self):
        # return ProductionOrder.objects.filter(status='UNCOMPLETED')
        return ProductionOrder.objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['work_stations'] = WorkStation.objects.all()
        return context


class AddProductionUnitToOrderView(View):
    def post(self, request, order_id):
        order = get_object_or_404(ProductionOrder, pk=order_id)
        form = QuickProductionUnitForm(request.POST)

        if form.is_valid():
            unit = form.save(commit=False)
            unit.production_order = order
            unit.status = 'NOT STARTED'
            unit.save()
            form.save_m2m()

        return redirect('uncompleted_orders')