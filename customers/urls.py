from django.urls import path
from customers.views import *

urlpatterns = [
    path('all-orders/', LoadOrders.as_view(), name='customer-all-orders'),
]
