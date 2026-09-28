from django.urls import path

from .views import (
    CustomerOrderListView,
    CustomerOrderCreateView,
    CustomerOrderDetailView,
)

from orders.edi_views import edi_test_xml, edi_test_send

app_name = "orders"


urlpatterns = [

    path(
        "new/",
        CustomerOrderCreateView.as_view(),
        name="customer_order_create",
    ),

    path(
        "<int:pk>/",
        CustomerOrderDetailView.as_view(),
        name="customer_order_detail",
    ),

]


urlpatterns += [
    path(
        "",
        CustomerOrderListView.as_view(),
        name="customer_order_list",
    ),

    path(
        "new/",
        CustomerOrderCreateView.as_view(),
        name="customer_order_create",
    ),

    path(
        "<int:pk>/",
        CustomerOrderDetailView.as_view(),
        name="customer_order_detail.js",
    ),
]

urlpatterns += [
    path(
        "edi/test-xml/",
        edi_test_xml,
        name="edi-test-xml",
    ),

    path(
        "edi/test-send/",
        edi_test_send,
        name="edi-test-send",
    ),
]