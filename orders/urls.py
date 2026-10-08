from django.urls import path

from .views import (
    CustomerOrderListView,
    CustomerOrderCreateView,
    CustomerOrderDetailView,
    cardboard_offer_search_view
)

from .help_views.products import customer_products
from .help_views.jassboard_calendar import JassBoardCalendarView

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


######## TEMPORARY

from django.urls import path

from .views import (
    ProductMaterialRequirementImportView, ProductMaterialRequirementBulkImportView
)


urlpatterns += [
    path(
        "material-requirements/import/",
        ProductMaterialRequirementImportView.as_view(),
        name="product_material_requirement_import",
    ),

    path(
        "material-requirements/bulk-import/",
        ProductMaterialRequirementBulkImportView.as_view(),
        name="product-material-requirement-bulk-import",
    ),
]


######################
# HELP VIEWS         #
######################

urlpatterns += [
    path(
        "ajax/customer-products/",
        customer_products,
        name="customer_products",
    ),

    path(
        "jassboard/calendar/",
        JassBoardCalendarView.as_view(),
        name="jassboard_calendar",
    ),
]

urlpatterns += [
    path(
        "cardboard/offers/search/",
        cardboard_offer_search_view,
        name="cardboard_offer_search",
    ),
]

