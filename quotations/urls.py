from django.urls import path
from .views import QuotationCreateView, QuotationDashboardView, QuotationDetailView, QuotationMaterialSearchView, \
    QuotationSettingsView, QuotationSheetCalculationView, QuotationProcessSettingsView

app_name = "quotations"

urlpatterns = [
    path("", QuotationDashboardView.as_view(), name="dashboard"),
    path("new/", QuotationCreateView.as_view(), name="create"),
    path("materials/", QuotationMaterialSearchView.as_view(), name="materials"),
    path("<int:quotation_id>/", QuotationDetailView.as_view(), name="detail"),
]

urlpatterns += [
    path(
        "settings/",
        QuotationSettingsView.as_view(),
        name="settings",
    ),
    path(
        "calculate-sheet/",
        QuotationSheetCalculationView.as_view(),
        name="calculate_sheet",
    ),

    path(
        "settings/processes/",
        QuotationProcessSettingsView.as_view(),
        name="process_settings",
    ),
]
