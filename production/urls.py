from django.urls import path
from production.views import *

urlpatterns = [
    path('', AllProductionOrders.as_view(), name='all-production-orders'),
    path('details/<int:production_order_id>/', ProductionDetails.as_view(), name='production-details'),
    path('workstation/all/', WorkStations.as_view(), name='production-workstations'),
    path('workstation/<int:workstation_id>', WorkStationDetails.as_view(), name='workstation-details'),
]