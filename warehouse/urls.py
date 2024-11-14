from django.urls import path
from warehouse.views import *


urlpatterns = [
    path('test/', TestView.as_view()),
    path('import_excel/', LoadExcelView.as_view(), name='import_excel'),
    path('load_wz/', LoadWZ.as_view()),
    path('orders/', OrderListView.as_view(), name='order_list'),
    path('deliveries/', DeliveriesView.as_view(), name='delivery_list'),
    path('delivery_detail/<int:delivery_id>/', DeliveryDetailView.as_view(), name="delivery-detail-view"),
    path('order_detail/<int:order_id>/', OrderDetailView.as_view(), name="order-detail-view"),
    path('process_delivery/<int:delivery_id>/', AddDeliveryToWarehouse.as_view(), name="process-delivery"),
]
