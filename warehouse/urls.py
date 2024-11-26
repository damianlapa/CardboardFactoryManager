from django.urls import path
from warehouse.views import *
from warehouse.ajax_views import *


app_name = 'warehouse'


urlpatterns = [
    path('test/', TestView.as_view()),
    path('import_excel/', LoadExcelView.as_view(), name='import_excel'),
    path('load_wz/', LoadWZ.as_view(), name='load-transport-document'),
    path('orders/', OrderListView.as_view(), name='order_list'),
    path('deliveries/', DeliveriesView.as_view(), name='delivery_list'),
    path('delivery_detail/<int:delivery_id>/', DeliveryDetailView.as_view(), name="delivery-detail-view"),
    path('order_detail/<int:order_id>/', OrderDetailView.as_view(), name="order-detail-view"),
    path('process_delivery/<int:delivery_id>/', AddDeliveryToWarehouse.as_view(), name="process-delivery"),
    path('warehouse/warehouses/', WarehouseListView.as_view(), name='warehouse-list-view'),
    path('warehouse/<int:warehouse_id>/', WarehouseView.as_view(), name='warehouse-detail-view'),
]

urlpatterns \
    += [
    # Inne ścieżki...
    path('deliveries/delivery/<int:delivery_id>/delete/', delete_delivery_ajax, name='delete_delivery_ajax'),
    # path('orders/<int:order_id>/settle/', settle_order, name='settle_order'),
]