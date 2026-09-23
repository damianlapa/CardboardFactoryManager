from warehouse.modern_views.customer_stock import CustomerStockListView
from django.urls import path


app_name = "modern_warehouse"


urlpatterns = [
    path(
        "customer-stock/",
        CustomerStockListView.as_view(),
        name="customer-stock-list",
    ),
]