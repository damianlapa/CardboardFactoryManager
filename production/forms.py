from django.forms import ModelForm, TextInput, Select, DateTimeInput, SelectMultiple
from django import forms
from production.models import *
from warehousemanager.models import Person


class ProductionOrderForm(forms.ModelForm):

    class Meta:
        model = ProductionOrder

        fields = [
            "id_number",
            "customer",
            "dimensions",
            "ordered_quantity",
            "quantity",
            "cardboard",
            "cardboard_dimensions",
            "status",
            "priority",
            "photopolymer",
            "punch",
            "notes",
        ]

        widgets = {
            "id_number": forms.TextInput(
                attrs={
                    "placeholder": "np. PAK 123/26",
                }
            ),

            "dimensions": forms.TextInput(
                attrs={
                    "placeholder": "np. 400x300x200",
                }
            ),

            "cardboard": forms.TextInput(
                attrs={
                    "placeholder": "np. 3B",
                }
            ),

            "cardboard_dimensions": forms.TextInput(
                attrs={
                    "placeholder": "np. 1200x800",
                }
            ),

            "notes": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Dodatkowe informacje...",
                }
            ),
        }

        labels = {
            "id_number": "Numer zlecenia",
            "customer": "Klient",
            "dimensions": "Wymiary produktu",
            "ordered_quantity": "Ilość zamówiona",
            "quantity": "Ilość produkcyjna",
            "cardboard": "Tektura",
            "cardboard_dimensions": "Wymiary tektury",
            "status": "Status",
            "priority": "Priorytet",
            "photopolymer": "Polimer",
            "punch": "Wykrojnik",
            "notes": "Notatki",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():
            if isinstance(
                field.widget,
                forms.CheckboxInput,
            ):
                continue

            current_class = (
                field.widget.attrs.get(
                    "class",
                    "",
                )
            )

            field.widget.attrs["class"] = (
                f"{current_class} production-form-control"
            ).strip()

        self.fields["priority"].widget.attrs.update({
            "class": "production-form-checkbox",
        })

        self.fields["customer"].queryset = (
            self.fields["customer"]
            .queryset
            .order_by("name")
        )

        self.fields["photopolymer"].queryset = (
            self.fields["photopolymer"]
            .queryset
            .filter(active=True)
            .order_by(
                "identification_number",
                "identification_letter",
            )
        )

        self.fields["punch"].queryset = (
            self.fields["punch"]
            .queryset
            .filter(active=True)
            .order_by(
                "type",
                "type_letter",
                "type_num",
            )
        )


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

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        kwargs.pop(
            "day",
            None,
        )

        super().__init__(
            *args,
            **kwargs,
        )

        datetime_formats = [
            "%Y-%m-%d %H:%M",
            "%Y-%m-%dT%H:%M",
        ]

        self.fields[
            "start"
        ].input_formats = datetime_formats

        self.fields[
            "end"
        ].input_formats = datetime_formats

        for name, field in self.fields.items():

            if name != "persons":
                existing_class = (
                    field.widget.attrs.get(
                        "class",
                        "",
                    )
                )

                field.widget.attrs[
                    "class"
                ] = (
                    f"{existing_class} form-control"
                ).strip()

        self.fields[
            "persons"
        ].widget.attrs.update({
            "class": "d-none",
        })


class QuickProductionUnitForm(ModelForm):
    class Meta:
        model = ProductionUnit
        fields = ['work_station', 'estimated_time', 'required_operators', 'required_helpers']
