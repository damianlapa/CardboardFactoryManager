from django.urls import path
from orders.views import *


urlpatterns = [
    # path('product/new', AddProduct.as_view(), name='new_product'),
    path('list/', OrdersView.as_view(), name='orders-view'),
    path('corders/', CardboardOrders.as_view(), name='cardboard-orders'),
    path('add-order/', AddOrder.as_view(), name='add-order')
]
