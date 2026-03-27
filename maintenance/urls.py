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
    PartSupplierCreateView,
    MaintenancePartUsageCreateView,
    MaintenanceDeliveryListView,
    MaintenanceDeliveryCreateView,
    MaintenanceDeliveryDetailView,
    MaintenanceDeliveryItemCreateView,
    MaintenanceDeliveryReceiveView
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
    path("machines/<int:machine_id>/parts/add/",
         MachinePartAssignmentCreateView.as_view(),
         name="machine-part-assignment-add"),
    path(
        "parts/<int:part_id>/suppliers/add/",
        PartSupplierCreateView.as_view(),
        name="part-supplier-add",
    ),
    path(
        "events/<int:event_id>/parts/add/",
        MaintenancePartUsageCreateView.as_view(),
        name="event-part-add",
    ),
]

urlpatterns += [
    path("deliveries/", MaintenanceDeliveryListView.as_view(), name="delivery-list"),
    path("deliveries/add/", MaintenanceDeliveryCreateView.as_view(), name="delivery-add"),
    path("deliveries/<int:delivery_id>/", MaintenanceDeliveryDetailView.as_view(), name="delivery-detail"),
    path("deliveries/<int:delivery_id>/items/add/", MaintenanceDeliveryItemCreateView.as_view(), name="delivery-item-add"),
    path("deliveries/<int:delivery_id>/receive/", MaintenanceDeliveryReceiveView.as_view(), name="delivery-receive"),
    ]