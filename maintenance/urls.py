from django.urls import path
from .views import (
    MachineListView,
    MachineDetailView,
    PartListView,
    PartDetailView,
    SupplierListView,
    SupplierDetailView,
    MaintenanceDashboardView
)

app_name = "maintenance"

urlpatterns = [
    path("", MaintenanceDashboardView.as_view(), name="dashboard"),
    path("machines/", MachineListView.as_view(), name="machine-list"),
    path("machines/<int:machine_id>/", MachineDetailView.as_view(), name="machine-detail"),

    path("parts/", PartListView.as_view(), name="part-list"),
    path("parts/<int:part_id>/", PartDetailView.as_view(), name="part-detail"),

    path("suppliers/", SupplierListView.as_view(), name="supplier-list"),
    path("suppliers/<int:supplier_id>/", SupplierDetailView.as_view(), name="supplier-detail"),
]