from django.shortcuts import render, HttpResponse, redirect
from django.views import View

from production.models import *
from production.forms import *


class ProductionMenu(View):
    def get(self, request):
        return render(request, 'production/production-menu.html', locals())


class AllProductionOrders(View):
    def get(self, request):
        title = 'Production Orders'
        production_orders = ProductionOrder.objects.all()
        return render(request, 'production/production-all.html', locals())


class ProductionDetails(View):
    def get(self, request, production_order_id):
        production_order_statuses = PRODUCTION_ORDER_STATUSES
        production_order = ProductionOrder.objects.get(id=production_order_id)
        production_units = ProductionUnit.objects.filter(production_order=production_order).order_by('sequence')
        return render(request, 'production/production-details.html', locals())


class ChangeProductionStatus(View):
    def get(self, request):
        production_order_id = int(request.GET.get('production-order-id'))
        status = request.GET.get('status')
        production_order = ProductionOrder.objects.get(id=production_order_id)
        production_order.status = status
        production_order.save()

        return redirect('production-details', production_order_id=production_order.id)


class AddProductionOrder(View):
    def get(self, request):
        form = ProductionOrderForm()
        return render(request, 'production/production-order-add.html', locals())

    def post(self, request):
        form = ProductionOrderForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            id_number = data['id_number']
            cardboard = data['cardboard']
            cardboard_dimensions = data['cardboard_dimensions']
            customer = data['customer']
            dimensions = data['dimensions']
            quantity = data['quantity']
            status = data['status']
            completed = data['completed']
            priority = data['priority']
            notes = data['notes']

            if customer:
                customer = Buyer.objects.get(name=customer)

            try:
                ProductionOrder.objects.get(id_number=id_number)
            except ObjectDoesNotExist:
                ProductionOrder.objects.create(id_number=id_number, cardboard=cardboard,
                                               cardboard_dimensions=cardboard_dimensions, customer=customer,
                                               dimensions=dimensions, quantity=quantity, status=status,
                                               completed=completed, priority=priority, notes=notes)
        return redirect('all-production-orders')


class WorkStations(View):
    def get(self, request):
        stations = WorkStation.objects.all()
        return render(request, 'production/workstations.html', locals())


class WorkStationDetails(View):
    def get(self, request, workstation_id):
        def get_date_str(some_date):
            date = some_date
            date_str = f'{date.year}-'
            if date.month < 10:
                date_str += '0'
            date_str += f'{date.month}-'
            if date.day < 10:
                date_str += '0'
            date_str += f'{date.day}'
            return date_str

        date_string = get_date_str(datetime.date.today())

        station = WorkStation.objects.get(id=workstation_id)
        units = ProductionUnit.objects.filter(work_station=station).order_by('order')
        return render(request, 'production/workstation-details.html', locals())


class AddProductionUnit(View):
    def get(self, request, order_id):
        production_order = ProductionOrder.objects.get(id=order_id)
        order_units = ProductionUnit.objects.filter(production_order=production_order)
        form = ProductionUnitForm(initial={'production_order': production_order, 'sequence': order_units.count() + 1})
        return render(request, 'production/production-unit-add.html', locals())

    def post(self, request, order_id):
        form = ProductionUnitForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            sequence = data['sequence']
            production_order = data['production_order']
            work_station = data['work_station']
            status = data['status']

            ProductionUnit.objects.create(production_order=production_order, work_station=work_station, status=status, sequence=sequence)

            return redirect('production-details', production_order_id=production_order.id)


class DeleteProductionUnit(View):
    def get(self, request, unit_id):
        unit = ProductionUnit.objects.get(id=unit_id)
        order_id = unit.production_order.id
        unit.delete()
        return redirect('production-details', production_order_id=order_id)