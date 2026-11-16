from warehouse.modern_views.customer_stock import CustomerStockListView

from django.urls import path
from warehouse.modern_views.products import ModernProductListView, ProductConfigurationEditView, ProductCreateView

app_name = "modern_warehouse"


urlpatterns = [
    path(
        "customer-stock/",
        CustomerStockListView.as_view(),
        name="customer-stock-list",
    ),
]


urlpatterns += [
    path(
        "products/",
        ModernProductListView.as_view(),
        name="products",
    ),
]

urlpatterns += [
    path("<int:pk>/edit/<str:kind>/", ProductConfigurationEditView.as_view(), name="product_config_edit"),
    path(
        "create/",
        ProductCreateView.as_view(),
        name="product_create",
    ),

]