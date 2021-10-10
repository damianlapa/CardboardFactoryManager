from django.urls import path
from production.views import *

urlpatterns = [
    path('', ProductionMenu.as_view(), name='production-menu'),
    path('orders/all/', AllProductionOrders.as_view(), name='all-production-orders'),
    path('order/details/<int:production_order_id>/', ProductionDetails.as_view(), name='production-details'),
    path('workstation/all/', WorkStations.as_view(), name='production-workstations'),
    path('workstation/<int:workstation_id>', WorkStationDetails.as_view(), name='workstation-details'),
    path('production-order-add/', AddProductionOrder.as_view(), name='production-order-add'),
    path('production-unit-add/<order_id>/', AddProductionUnit.as_view(), name='production-unit-add')
]