# warehouse/urls.py

from django.urls import path
from warehouse.views import *
from warehouse.ajax_views import *
from warehouse.load_csv_views import *
from warehouse.statstics_views import *
from warehouse.create_order_views import GenerateOrderInlineView
from warehouse.sales_reports_views import sales_report_view, sales_pdf_view
from warehouse.product_complex_views import *
from warehouse.price_list_view import PriceListUploadView
from warehouse.monthly_reports_views import MonthlyWarehouseReportView


app_name = 'warehouse'

urlpatterns = [
    path('load_wz/', LoadWZ.as_view(), name='load-transport-document'),
    path('orders/', OrderListView.as_view(), name='order_list'),
    path('order_detail/<int:order_id>/', OrderDetailView.as_view(), name="order-detail-view"),
    path('warehouse/warehouses/', WarehouseListView.as_view(), name='warehouse-list-view'),
    path('warehouse/<int:warehouse_id>/', WarehouseView.as_view(), name='warehouse-detail-view'),
    path('stock-details/<int:stock_id>/', StockView.as_view(), name='stock-details'),
]

urlpatterns += [
    path('generate-order-inline/<int:order_id>/', GenerateOrderInlineView.as_view(), name='generate_order_inline'),
]

# delivery urls
urlpatterns += [
    path('deliveries/', DeliveriesView.as_view(), name='delivery_list'),
    path('delivery_detail/<int:delivery_id>/', DeliveryDetailView.as_view(), name="delivery-detail-view"),
    path('delivery_update/<int:delivery_id>/', LoadDeliveryToGSFile.as_view(), name="load-delivery-togsf-view"),
    path('add-delivery-item/', AddDeliveryItem.as_view(), name='add-delivery-item'),
    path('deliveries/statistics/', DeliveriesStatistics.as_view(), name='deliveries-statistics'),
    path('deliveries/delivery/<int:delivery_id>/delete/', delete_delivery_ajax, name='delete_delivery_ajax'),
    path('deliveries/delivery/<int:delivery_id>/edit/', DeliveryEditView.as_view(), name='delivery-edit'),
    path('delivery_special_detail/<int:delivery_id>/', DeliverySpecialDetailView.as_view(), name="delivery-special-detail-view"),
    path('add-delivery-special-item/', AddDeliverySpecialItem.as_view(), name='add-delivery-special-item'),
    path('process_delivery/<int:delivery_id>/', AddDeliveryToWarehouse.as_view(), name="process-delivery"),
    path('process_delivery/<int:delivery_id>/<int:item_id>/', AddDeliveryItemToWarehouse.as_view(), name="process-delivery-item"),
    path('process_delivery_special/<int:delivery_id>/', AddDeliverySpecialToWarehouse.as_view(), name="process-delivery-special"),
    path('process_delivery_special/<int:delivery_id>/<int:item_id>/', AddDeliverySpecialItemToWarehouse.as_view(), name="process-delivery-special-item"),
]

urlpatterns += [
    path('orders/<int:order_id>/settle/', settle_order, name='settle_order'),
]

urlpatterns += [
    path('orders/status/', order_status, name='order_status'),
]

urlpatterns += [
    path('sells/list/', SellProductList.as_view(), name='sells-list-view'),
    path('sells/create/', ProductSell3CreateView.as_view(), name="productsell3-create")
]

# temporary
urlpatterns += [
    path('import-csv/', import_csv_view, name='import_csv'),
]

urlpatterns += [
    path('customer-distribution/', customer_distribution, name='customer-distribution'),
    path('customer-orders/', customer_orders, name='customer-orders-statistic'),
]

# palette
urlpatterns += [
    path('palette/', PaletteView.as_view(), name='palette-list-view'),
]

# product sell
urlpatterns += [
    path('product-sell3/', add_product_sell3, name='add_product_sell3'),
    path('add-products/', assign_products_to_orders),
    path('add-price/', assign_price_to_orders),
    path('clr/', clear_orders),
]

# report
urlpatterns += [
    path('sales-report/', sales_report_view, name='sales_report'),
    path('sales-report/pdf/', sales_pdf_view, name='sales_pdf'),
]

urlpatterns += [
    path("assembly/new/", AssemblyCreateView.as_view(), name="assembly_create"),
    path("assembly/", AssemblyListView.as_view(), name="assembly_list"),
    path("assembly/<int:pk>/", AssemblyDetailView.as_view(), name="assembly_detail"),
]

urlpatterns += [
    path("orders/<int:order_id>/add-shift/", AddShiftView.as_view(), name="add_shift"),
]

# urlpatterns += [
#     path("orders/<int:order_id>/add-shift/", AddDeliveryItemToWarehouse.as_view(), name="add_shift"),
# ]

# price list
urlpatterns += [
    path('price_list/upload/', PriceListUploadView.as_view(), name='price_list-upload'),
]

urlpatterns += [
    path('orders/add/', AddOrdersManually.as_view(), name='add-orders'),
]

urlpatterns += [
    path("warehouse-stock/<int:pk>/history/", WarehouseStockHistoryDetailView.as_view(), name="warehouse_stock_history"),
    path("warehouse-stock/<int:pk>/", WarehouseStockDetailView.as_view(), name="warehouse_stock_detail"),
]

urlpatterns += [
    path("bom/<int:bom_id>/create-order/", CreateOrderFromBOMView.as_view(), name="bom_create_order"),
]

urlpatterns += [
    path("bom/<int:pk>/", BOMDetailView.as_view(), name="bom_detail"),
    path("boms/", BOMListView.as_view(), name="bom_list"),
]

urlpatterns += [
    path("monthly-report/", MonthlyWarehouseReportView.as_view(), name="monthly_report"),
]

urlpatterns += [
    path("products/packaging/", ProductPackagingListView.as_view(), name="product_packaging_list"),
    path("products/packaging/upsert/", ProductPackagingUpsertAjaxView.as_view(), name="product_packaging_upsert_ajax"),
]


urlpatterns += [
    path('settlement/<int:settlement_id>/undo/', undo_order_settlement, name='undo_order_settlement'),
    path("sell/<int:sell_id>/undo/", undo_product_sell, name="undo_product_sell"),
    path("delivery-item/<int:item_id>/undo-process/", undo_delivery_item_process, name="undo_delivery_item_process"),
]

urlpatterns += [
    path('warehouses/refresh_warehouses_values/', refresh_warehouses_values, name='refresh_warehouses_values'),
    path(
        "orders/profitability/",
        OrderProfitabilityListView.as_view(),
        name="order-profitability-list"
    ),
]
