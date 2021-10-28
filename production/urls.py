from django.urls import path
from production.views import *

urlpatterns = [
    path('', ProductionMenu.as_view(), name='production-menu'),
    path('orders/all/', AllProductionOrders.as_view(), name='all-production-orders'),
    path('order/details/<int:production_order_id>/', ProductionDetails.as_view(), name='production-details'),
    path('order/details/change/', ChangeProductionStatus.as_view(), name='production-details-change'),
    path('workstation/all/', WorkStations.as_view(), name='production-workstations'),
    path('workstation/<int:workstation_id>', WorkStationDetails.as_view(), name='workstation-details'),
    path('production-order-add/', AddProductionOrder.as_view(), name='production-order-add'),
    path('unit/details/<int:unit_id>/', ProductionUnitDetails.as_view(), name='unit-details'),
    path('production-unit-add/<order_id>/', AddProductionUnit.as_view(), name='production-unit-add'),
    path('production-unit-delete/<int:unit_id>/', DeleteProductionUnit.as_view(), name='delete-production-unit'),
    path('unit/edit/<int:unit_id>/', EditProductionUnit.as_view(), name='unit-edit'),
]

# production units
urlpatterns += [
    path('unit/start/<int:unit_id>/', StartProductionUnit.as_view(), name='unit-start'),
    path('unit/finish/<int:unit_id>/', FinishProductionUnit.as_view(), name='unit-finish'),
    path('unit/plan/<int:unit_id>/', PlanProductionUnit.as_view(), name='unit-plan'),
    path('unit/remove/<int:unit_id>/', RemoveProductionUnit.as_view(), name='unit-remove'),
    path('unit/up/<int:unit_id>/', UpProductionUnit.as_view(), name='unit-up'),
    path('unit/down/<int:unit_id>/', DownProductionUnit.as_view(), name='unit-down'),
]

# worker
urlpatterns += [
    path('workers-by-month/<int:year>/<int:month>/', WorkersByMonth.as_view(), name='worker-month'),
    path('worker-efficiency/<int:year>/<int:month>/<int:worker_id>/', WorkerEfficiency.as_view(), name='worker-efficiency'),
    path('worker-efficiency-pdf/<int:year>/<int:month>/<int:worker_id>/', WorkerEfficiencyPrintPDF.as_view(), name='worker-efficiency-pdf')
]

# work stations
urlpatterns += [
    path('station-efficiency/<int:year>/<int:month>/<int:station_id>/', WorkStationEfficiency.as_view(), name='station-efficiency'),
    path('station-efficiency-pdf/<int:year>/<int:month>/<int:station_id>/', StationEfficiencyPrintPDF.as_view(), name='station-efficiency-pdf'),
]