from django.urls import path

from .views import QuotationDashboardView


app_name = "quotations"

urlpatterns = [
    path("", QuotationDashboardView.as_view(), name="dashboard"),
]
