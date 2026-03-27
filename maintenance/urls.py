from django.urls import path
from .views import (
    MaintenanceDashboardView,
    MachineListView,
    MachineDetailView,
    PartListView,
    PartDetailView,
    SupplierListView,
    SupplierDetailView,
    MachineCreateView,
    PartCreateView,
    SupplierCreateView,
    SupplierContactCreateView,
    MaintenanceEventCreateView,
    MachinePartAssignmentCreateView,
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

urlpatterns += [
    path("machines/add/", MachineCreateView.as_view(), name="machine-add"),
    path("parts/add/", PartCreateView.as_view(), name="part-add"),
    path("suppliers/add/", SupplierCreateView.as_view(), name="supplier-add"),
    path("suppliers/<int:supplier_id>/contacts/add/", SupplierContactCreateView.as_view(), name="supplier-contact-add"),
    path("machines/<int:machine_id>/events/add/", MaintenanceEventCreateView.as_view(), name="event-add"),
    path("machines/<int:machine_id>/parts/add/", MachinePartAssignmentCreateView.as_view(), name="machine-part-assignment-add",
    ),
]