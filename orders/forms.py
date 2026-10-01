from django import forms

from django.core.exceptions import ValidationError

from .models import (
    CustomerOrder,
    MaterialRequirement,
)

from warehouse.models import Provider


from .services.scores import parse_scores


class CardboardPriceListImportForm(forms.Form):

    provider = forms.ModelChoiceField(
        queryset=Provider.objects.all().order_by("name"),
        label="Dostawca",
    )

    file = forms.FileField(
        label="Plik PDF",
        help_text="Wybierz cennik dostawcy w formacie PDF.",
    )

    def clean_file(self):
        file = self.cleaned_data["file"]

        name = (file.name or "").lower()

        if not name.endswith(".pdf"):
            raise forms.ValidationError(
                "Importer obsługuje obecnie tylko pliki PDF."
            )

        return file


class CustomerOrderForm(forms.ModelForm):

    class Meta:
        model = CustomerOrder

        fields = (
            "customer",
            "product",
            "quantity",
            "order_date",
            "requested_delivery_date",
            "notes",
        )

        widgets = {
            "quantity": forms.NumberInput(
                attrs={
                    "min": 1,
                }
            ),

            "order_date": forms.DateInput(
                attrs={
                    "type": "date",
                }
            ),

            "requested_delivery_date": forms.DateInput(
                attrs={
                    "type": "date",
                }
            ),

            "notes": forms.Textarea(
                attrs={
                    "rows": 3,
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        Product = self.fields["product"].queryset.model

        # Domyślnie brak produktów
        self.fields["product"].queryset = Product.objects.none()

        # POST - klient został już wybrany
        if "customer" in self.data:
            try:
                customer_id = int(self.data.get("customer"))

                self.fields["product"].queryset = (
                    Product.objects
                    .filter(order__customer_id=customer_id)
                    .distinct()
                    .order_by("name")
                )

            except (TypeError, ValueError):
                pass

        # Edycja istniejącego zamówienia
        elif self.instance.pk and self.instance.customer_id:
            self.fields["product"].queryset = (
                Product.objects
                .filter(order__customer_id=self.instance.customer_id)
                .distinct()
                .order_by("name")
            )


class MaterialRequirementForm(forms.ModelForm):

    scores = forms.CharField(
        required=False,
        label="Bigi",
        help_text="Np. 100/400/100",
        widget=forms.TextInput(
            attrs={
                "placeholder": "np. 100/400/100",
            }
        ),
    )

    class Meta:
        model = MaterialRequirement

        fields = (
            "sheet_length",
            "sheet_width",
            "pieces_per_sheet",
            "required_sheet_quantity",
            "layers",
            "flute",
            "min_gsm",
            "min_ect",
            "cover",
            "scores",
            "notes",
        )

        widgets = {
            "notes": forms.Textarea(
                attrs={
                    "rows": 3,
                }
            ),
        }

    def clean(self):
        cleaned_data = super().clean()

        scores = cleaned_data.get("scores")
        width = cleaned_data.get("sheet_width")

        if not scores:
            return cleaned_data

        if not width:
            self.add_error(
                "scores",
                "Najpierw podaj szerokość arkusza.",
            )
            return cleaned_data

        try:
            parse_scores(
                scores,
                width=width,
            )

        except ValidationError as e:
            self.add_error(
                "scores",
                e.messages[0],
            )

        return cleaned_data


class MaterialPurchaseForm(forms.Form):

    requirement_id = forms.IntegerField(
        widget=forms.HiddenInput(),
    )

    price_list_item_id = forms.IntegerField(
        widget=forms.HiddenInput(),
    )

    order_number = forms.CharField(
        max_length=64,
        label="Numer zamówienia u dostawcy",
    )

    order_date = forms.DateField(
        label="Data zamówienia",
        widget=forms.DateInput(
            attrs={
                "type": "date",
            }
        ),
    )

    delivery_date = forms.DateField(
        label="Oczekiwana data dostawy",
        widget=forms.DateInput(
            attrs={
                "type": "date",
            }
        ),
    )


######## TEMPORARY

from django import forms


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault(
            "widget",
            MultipleFileInput(
                attrs={
                    "accept": ".txt",
                }
            ),
        )
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean

        if isinstance(data, (list, tuple)):
            return [
                single_file_clean(file, initial)
                for file in data
            ]

        return [
            single_file_clean(data, initial)
        ]


class ProductMaterialRequirementImportForm(forms.Form):
    files = MultipleFileField(
        label="Pliki historyczne",
        help_text="Wybierz pliki TXT z historią zamówień.",
    )