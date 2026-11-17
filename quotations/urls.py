from django.urls import path
from .views import QuotationCreateView, QuotationDashboardView, QuotationDetailView, QuotationMaterialSearchView

app_name = "quotations"

urlpatterns = [
    path("", QuotationDashboardView.as_view(), name="dashboard"),
    path("new/", QuotationCreateView.as_view(), name="create"),
    path("materials/", QuotationMaterialSearchView.as_view(), name="materials"),
    path("<int:quotation_id>/", QuotationDetailView.as_view(), name="detail"),
]
