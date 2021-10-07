from django.shortcuts import render, HttpResponse
from django.views import View


from production.models import *


class AllProductionOrders(View):
    def get(self, request):
        production_orders = ProductionOrder.objects.all()
        return render(request, 'production/production-all.html', locals())


class ProductionDetails(View):
    def get(self, request, production_order_id):
        production_order = ProductionOrder.objects.get(id=production_order_id)
        production_units = ProductionUnit.objects.filter(production_order=production_order)
        production_units = production_units.order_by('start')

        return render(request, 'production/production-details.html', locals())


class WorkStations(View):
    def get(self, request):
        stations = WorkStation.objects.all()
        return render(request, 'production/workstations.html', locals())


class WorkStationDetails(View):
    def get(self, request, workstation_id):
        station = WorkStation.objects.get(id=workstation_id)
        units = ProductionUnit.objects.filter(work_station=station).order_by('order')
        return render(request, 'production/workstation-details.html', locals())
