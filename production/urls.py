from django.urls import path
from production.views import *

urlpatterns = [
    path('', AllProductionOrders.as_view(), name='all-production-orders'),
    path('details/<int:production_order_id>/', ProductionDetails.as_view(), name='production-details')
]