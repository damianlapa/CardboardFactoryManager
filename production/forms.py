from django.forms import ModelForm, TextInput, Select, DateTimeInput, SelectMultiple
from django import forms
from production.models import *
from warehousemanager.models import Person


class ProductionOrderForm(ModelForm):
    class Meta:
        model = ProductionOrder
        # fields = ('id_number', 'cardboard', 'cardboard_dimensions', 'customer', 'dimensions', 'quantity', 'status', 'notes')
        fields = '__all__'


class ProductionUnitForm(forms.ModelForm):
    class Meta:
        model = ProductionUnit
        fields = [
            "sequence",
            "work_station",
            "status",
            "persons",
            "estimated_time",
            "start",
            "end",
            "quantity_start",
            "quantity_end",
            "notes",
        ]

        widgets = {
            "start": forms.DateTimeInput(
                attrs={
                    "type": "text",
                    "class": "form-control js-datetime-picker",
                    "placeholder": "rrrr-mm-dd gg:mm",
                    "autocomplete": "off",
                },
                format="%Y-%m-%d %H:%M",
            ),
            "end": forms.DateTimeInput(
                attrs={
                    "type": "text",
                    "class": "form-control js-datetime-picker",
                    "placeholder": "rrrr-mm-dd gg:mm",
                    "autocomplete": "off",
                },
                format="%Y-%m-%d %H:%M",
            ),
        }

    def __init__(self, *args, **kwargs):
        day = kwargs.pop("day", None)
        super().__init__(*args, **kwargs)

        self.fields["start"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["end"].input_formats = ["%Y-%m-%dT%H:%M"]

        for name, field in self.fields.items():
            if name not in ("persons",):
                field.widget.attrs.setdefault("class", "form-control")

        self.fields["persons"].widget.attrs.update({
            "class": "d-none",
        })


class QuickProductionUnitForm(ModelForm):
    class Meta:
        model = ProductionUnit
        fields = ['work_station', 'estimated_time', 'required_operators', 'required_helpers']
