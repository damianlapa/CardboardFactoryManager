from django.urls import path
from warehouse.views import *
from warehouse.ajax_views import *
#
#
app_name = 'warehouse'
#
#
urlpatterns = [
    path('test/', TestView.as_view()),
    path('import_excel/', LoadExcelView.as_view(), name='import_excel'),
    path('load_wz/', LoadWZ.as_view(), name='load-transport-document'),
    path('orders/', OrderListView.as_view(), name='order_list'),
    path('deliveries/', DeliveriesView.as_view(), name='delivery_list'),
    path('delivery_detail/<int:delivery_id>/', DeliveryDetailView.as_view(), name="delivery-detail-view"),
    path('delivery_update/<int:delivery_id>/', LoadDeliveryToGSFile.as_view(), name="load-delivery-togsf-view"),
    path('order_detail/<int:order_id>/', OrderDetailView.as_view(), name="order-detail-view"),
    path('process_delivery/<int:delivery_id>/', AddDeliveryToWarehouse.as_view(), name="process-delivery"),
    path('warehouse/warehouses/', WarehouseListView.as_view(), name='warehouse-list-view'),
    path('warehouse/<int:warehouse_id>/', WarehouseView.as_view(), name='warehouse-detail-view'),
    path('add-delivery-item/', AddDeliveryItem.as_view(), name='add-delivery-item'),
    path('deliveries/statistics/', DeliveriesStatistics.as_view(), name='deliveries-statistics'),
    path('stock-details/<int:stock_id>/', StockView.as_view(), name='stock-details')
]

urlpatterns \
    += [
    # Inne ścieżki...
    path('deliveries/delivery/<int:delivery_id>/delete/', delete_delivery_ajax, name='delete_delivery_ajax'),
    path('orders/<int:order_id>/settle/', settle_order, name='settle_order'),
]

urlpatterns += [
    path('orders/status/', order_status, name='order_status'),
]

urlpatterns += [
    path('sells/list/', SellProductList.as_view(), name='sells-list-view'),
    path('sells/create/', ProductSellCreateView.as_view(), name="productsell-create")
]
