from django import forms
from .models import MaintenanceEvent, MaintenancePartUsage

from .models import (
    Machine,
    MachinePart,
    MaintenanceSupplier,
    MaintenanceSupplierContact,
    MachinePartAssignment,
    MachinePartSupplier
)

from .models import MaintenanceDelivery, MaintenanceDeliveryItem


class MaintenanceEventForm(forms.ModelForm):
    class Meta:
        model = MaintenanceEvent
        fields = ["event_type", "date", "description", "downtime_hours"]


class MaintenancePartUsageForm(forms.ModelForm):
    class Meta:
        model = MaintenancePartUsage
        fields = ["part", "warehouse_stock", "quantity"]


class MachineForm(forms.ModelForm):
    class Meta:
        model = Machine
        fields = [
            "name",
            "code",
            "serial_number",
            "manufacturer",
            "location",
            "description",
            "is_active",
        ]


class MachinePartForm(forms.ModelForm):
    initial_quantity = forms.IntegerField(
        min_value=0,
        initial=0,
        label="Stan początkowy"
    )

    class Meta:
        model = MachinePart
        fields = [
            "name",
            "code",
            "category",
            "producer",
            "unit",
            "min_quantity",
            "recommended_quantity",
            "description",
            "is_active",
        ]


class MaintenanceSupplierForm(forms.ModelForm):
    class Meta:
        model = MaintenanceSupplier
        fields = [
            "name",
            "shortcut",
            "website",
            "city",
            "address",
            "notes",
            "is_active",
        ]


class MaintenanceSupplierContactForm(forms.ModelForm):
    class Meta:
        model = MaintenanceSupplierContact
        fields = [
            "name",
            "role",
            "contact_type",
            "phone",
            "email",
            "is_main",
            "notes",
        ]


class MachinePartAssignmentForm(forms.ModelForm):
    class Meta:
        model = MachinePartAssignment
        fields = [
            "part",
            "quantity_needed",
            "is_critical",
            "notes",
        ]


class MachinePartSupplierForm(forms.ModelForm):
    class Meta:
        model = MachinePartSupplier
        fields = [
            "supplier",
            "supplier_code",
            "is_preferred",
            "lead_time_days",
            "notes",
        ]


class MaintenanceDeliveryForm(forms.ModelForm):
    class Meta:
        model = MaintenanceDelivery
        fields = [
            "supplier",
            "delivery_date",
            "document_number",
            "invoice_number",
            "notes",
        ]


class MaintenanceDeliveryItemForm(forms.ModelForm):
    class Meta:
        model = MaintenanceDeliveryItem
        fields = [
            "part",
            "warehouse",
            "quantity",
            "unit_price_net",
            "supplier_code",
            "notes",
        ]
