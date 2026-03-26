from django import forms
from .models import MaintenanceEvent, MaintenancePartUsage


class MaintenanceEventForm(forms.ModelForm):
    class Meta:
        model = MaintenanceEvent
        fields = ["machine", "event_type", "date", "description", "downtime_hours"]


class MaintenancePartUsageForm(forms.ModelForm):
    class Meta:
        model = MaintenancePartUsage
        fields = ["part", "warehouse_stock", "quantity"]