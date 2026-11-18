import datetime

from django import forms

from django.forms import BaseInlineFormSet, inlineformset_factory
from django.core.exceptions import ValidationError
from production.models import WorkStation
from .models import Quotation, QuotationCustomer, QuotationItem

from .services.items import sum_work_hours


class QuotationCreateForm(forms.Form):
    customer = forms.ModelChoiceField(
        label="Klient wycen",
        queryset=QuotationCustomer.objects.none(),
        required=False,
        empty_label="— Wybierz firmę —",
        widget=forms.Select(attrs={"aria-describedby": "id_customer_help id_customer_errors"}),
    )
    new_customer_name = forms.CharField(
        label="Nazwa nowej firmy",
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            "placeholder": "Wpisz nazwę, jeśli firmy nie ma na liście",
            "autocomplete": "organization",
            "aria-describedby": "id_new_customer_name_help id_new_customer_name_errors",
        }),
    )
    date = forms.DateField(
        label="Data wyceny",
        initial=datetime.date.today,
        input_formats=["%Y-%m-%d", "%d.%m.%Y"],
        widget=forms.DateInput(
            format="%Y-%m-%d",
            attrs={"type": "date", "aria-describedby": "id_date_errors"},
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["customer"].queryset = QuotationCustomer.objects.order_by("name", "pk")

    def clean(self):
        cleaned_data = super().clean()
        customer = cleaned_data.get("customer")
        new_name = cleaned_data.get("new_customer_name", "")
        if "customer" in self.errors or "new_customer_name" in self.errors:
            return cleaned_data
        if customer and new_name:
            raise forms.ValidationError("Wybierz klienta z listy albo wpisz nową firmę — uzupełnij tylko jedną z tych opcji.")
        if not customer and not new_name:
            raise forms.ValidationError("Wybierz klienta wycen lub wpisz nazwę nowej firmy.")
        return cleaned_data


class WorkEntryForm(forms.Form):
    work_station = forms.ModelChoiceField(queryset=WorkStation.objects.all())
    employees = forms.IntegerField(min_value=1)
    hours = forms.DecimalField(min_value=0, max_digits=10, decimal_places=2)


class QuotationItemForm(forms.ModelForm):
    work_entries = forms.JSONField(required=False, initial=list, widget=forms.HiddenInput)
    print_colors = forms.JSONField(
        required=False,
        initial=list,
        widget=forms.HiddenInput,
    )

    class Meta:
        model = QuotationItem
        fields = (
            "packaging_type",
            "width",
            "length",
            "height",
            "quantity",
            "material",
            "products_per_sheet",
            "sheet_width",
            "sheet_length",
            "material_price",
            "hours",
            "hours_manual",
            "price",
        )

        widgets = {
            "material": forms.HiddenInput,
            "hours_manual": forms.HiddenInput,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["packaging_type"].queryset = self.fields["packaging_type"].queryset.order_by("code")
        self.fields["packaging_type"].empty_label = "— FEFCO —"
        if self.instance.pk:
            self.initial["work_entries"] = [
                {"work_station": entry.work_station_id, "employees": entry.employees, "hours": str(entry.hours)}
                for entry in self.instance.work_entries.all()
            ]
        if (
            self.instance.pk
            and not self.is_bound
            and not self.instance.hours_manual
        ):
            self.initial["hours"] = sum_work_hours(
                self.initial["work_entries"]
            )
        for name, field in self.fields.items():
            field.widget.attrs["aria-label"] = field.label or name
            if isinstance(field, forms.DecimalField):
                field.widget.attrs.update({"min": "0", "step": "0.01"})

        if self.instance.pk:
            self.initial["print_colors"] = [
                {
                    "color_name": color.color_name,
                    "consumption_per_1000": str(
                        color.consumption_per_1000
                    ),
                }
                for color in self.instance.print_colors.all()
            ]

    def clean(self):
        cleaned_data = super().clean()

        if (
            not cleaned_data.get("hours_manual")
            and "work_entries" in cleaned_data
        ):
            cleaned_data["hours"] = sum_work_hours(
                cleaned_data["work_entries"]
            )

        return cleaned_data


    def clean_print_colors(self):
        if self.add_prefix("print_colors") not in self.data:
            raise ValidationError(
                "Brak danych nadruku. Odśwież formularz."
            )

        entries = self.cleaned_data.get("print_colors")

        if entries is None:
            entries = []

        if (
            not isinstance(entries, list)
            or len(entries) > 100
        ):
            raise ValidationError(
                "Nadruk musi być listą zawierającą "
                "najwyżej 100 kolorów."
            )

        result = []

        for index, entry in enumerate(entries, 1):
            if not isinstance(entry, dict):
                raise ValidationError(
                    f"Kolor #{index}: niepoprawne dane."
                )

            form = PrintColorForm(entry)

            if not form.is_valid():
                raise ValidationError(
                    f"Kolor #{index}: podaj nazwę oraz "
                    "nieujemne zużycie z maksymalnie "
                    "4 miejscami po przecinku."
                )

            result.append({
                "color_name": form.cleaned_data["color_name"],
                "consumption_per_1000": str(
                    form.cleaned_data["consumption_per_1000"]
                ),
            })

        return result

    def clean_work_entries(self):
        if self.add_prefix("work_entries") not in self.data:
            raise ValidationError("Brak danych godzin pracy. Odśwież formularz.")
        entries = self.cleaned_data.get("work_entries")
        if entries is None:
            entries = []
        if not isinstance(entries, list) or len(entries) > 100:
            raise ValidationError("Godziny pracy muszą być listą zawierającą najwyżej 100 wpisów.")
        result = []
        for index, entry in enumerate(entries, 1):
            if not isinstance(entry, dict):
                raise ValidationError(f"Wpis godzin #{index}: niepoprawne dane.")
            form = WorkEntryForm(entry)
            if not form.is_valid():
                raise ValidationError(f"Wpis godzin #{index}: wybierz stanowisko, podaj co najmniej 1 pracownika i nieujemne godziny z maksymalnie 2 miejscami po przecinku.")
            data = form.cleaned_data
            result.append({"work_station": data["work_station"].pk, "employees": data["employees"], "hours": str(data["hours"])})
        return result


class BaseQuotationItemFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        seen = set()
        for form in self.forms:
            item = form.cleaned_data.get("id") if hasattr(form, "cleaned_data") else None
            if item:
                if item.quotation_id != self.instance.pk or item.pk != form.instance.pk or item.pk in seen:
                    raise ValidationError("Niepoprawna lub powtórzona pozycja wyceny. Odśwież stronę.")
                seen.add(item.pk)


QuotationItemFormSet = inlineformset_factory(
    Quotation, QuotationItem, form=QuotationItemForm,
    formset=BaseQuotationItemFormSet, extra=0, can_delete=False,
)


class PrintColorForm(forms.Form):
    color_name = forms.CharField(
        max_length=100,
    )
    consumption_per_1000 = forms.DecimalField(
        max_digits=12,
        decimal_places=4,
        min_value=0,
    )