# warehouse/forms.py

import datetime

from django.forms import ModelForm, Form, FileField, inlineformset_factory, BaseInlineFormSet
from warehouse.models import (Product, DeliverySpecialItem, DeliveryItem, Delivery, DeliveryPalette,
                              ProductComplexAssembly, ProductComplexParts, WarehouseStock, OrderToOrderShift, PriceList, PriceListItem, Provider)
from django.core.validators import FileExtensionValidator
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Buyer, Order


class DeliveryItemForm(ModelForm):
    class Meta:
        model = DeliveryItem
        fields = ['delivery', 'order', 'quantity', 'palettes_quantity']
        # fields = '__all__'


class DeliverySpecialItemForm(ModelForm):
    class Meta:
        model = DeliverySpecialItem
        fields = '__all__'


class CSVUploadForm(Form):
    file = FileField(label="Plik CSV do importu")


DeliveryPaletteFormSet = inlineformset_factory(
    Delivery,
    DeliveryPalette,
    fields=('palette', 'quantity'),
    extra=1,
    can_delete=True
)


class DeliveryForm(ModelForm):
    class Meta:
        model = Delivery
        fields = ('date', 'car_number', 'telephone', 'description', 'processed', 'updated')


class ManuallyOrdersForm(forms.Form):
    SOURCE_CHOICES = [
        ('sheet', 'Wiersz w Google Sheet'),
        ('provider', 'Zamówienie u dostawcy'),
    ]

    source = forms.ChoiceField(
        choices=SOURCE_CHOICES,
        label='Źródło danych'
    )

    # wariant 1: Google Sheet
    sheet_row = forms.IntegerField(
        required=False,
        min_value=1,
        label='Numer wiersza w Google Sheet'
    )

    # wariant 2: dostawca + numer zamówienia
    provider = forms.ModelChoiceField(
        queryset=Provider.objects.all(),
        required=False,
        label='Dostawca'
    )
    provider_order_number = forms.CharField(
        required=False,
        label='Numer zamówienia u dostawcy'
    )

    year = forms.IntegerField(
        required=True,
        label='Rok zamówienia',
        min_value=2021,
        max_value=datetime.date.today().year,
        initial=datetime.date.today().year
    )

    def clean(self):
        cleaned_data = super().clean()
        source = cleaned_data.get('source')
        sheet_row = cleaned_data.get('sheet_row')
        provider = cleaned_data.get('provider')
        provider_order_number = cleaned_data.get('provider_order_number')

        if source == 'sheet':
            if not sheet_row:
                self.add_error('sheet_row', 'Podaj numer wiersza w Google Sheet.')
            # opcjonalnie czyścimy drugi wariant
            cleaned_data['provider'] = None
            cleaned_data['provider_order_number'] = ''

        elif source == 'provider':
            if not provider:
                self.add_error('provider', 'Wybierz dostawcę.')
            if not provider_order_number:
                self.add_error(
                    'provider_order_number',
                    'Podaj numer zamówienia u dostawcy.'
                )
            # opcjonalnie czyścimy pierwszy wariant
            cleaned_data['sheet_row'] = None

        return cleaned_data


# class ProductSell2Form(ModelForm):
#     class Meta:
#         model = ProductSell2
#         fields = ['product', 'quantity', 'price', 'date']


class OrderToOrderShiftForm(forms.ModelForm):
    class Meta:
        model = OrderToOrderShift
        exclude = ["order_from"]  # "value" również, jeśli istnieje i jest wyliczane
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
        }

    def clean_quantity(self):
        q = self.cleaned_data.get("quantity")
        if q is None or q <= 0:
            raise forms.ValidationError("Quantity must be a positive number.")
        return q


class ProductComplexAssemblyForm(forms.ModelForm):
    class Meta:
        model = ProductComplexAssembly
        fields = ["date", "product", "quantity"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "quantity": forms.NumberInput(attrs={"min": 1}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["product"].queryset = (
            Product.objects
            .filter(name__icontains="KOMPLET")
            .order_by("name")
        )


class ProductComplexPartsForm(forms.ModelForm):
    class Meta:
        model = ProductComplexParts
        fields = ["part", "quantity"]
        widgets = {
            "quantity": forms.NumberInput(attrs={"min": 0}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["part"].queryset = (
            WarehouseStock.objects
            .filter(quantity__gt=0)
            .order_by("-warehouse", "stock__name")
        )


class PartsInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        seen = set()
        for form in self.forms:
            if form.cleaned_data.get("DELETE", False):
                continue
            if not form.cleaned_data or form.cleaned_data.get("part") is None:
                # pusta linia – ok, zostanie zignorowana
                continue
            part = form.cleaned_data["part"]
            qty = form.cleaned_data.get("quantity") or 0
            if qty < 0:
                form.add_error("quantity", "Ilość nie może być ujemna.")
            if part in seen:
                form.add_error("part", "Ta pozycja części już jest na liście.")
            seen.add(part)


PartsFormSet = inlineformset_factory(
    parent_model=ProductComplexAssembly,
    model=ProductComplexParts,
    form=ProductComplexPartsForm,
    formset=PartsInlineFormSet,
    fields=["part", "quantity"],
    extra=3,           # ile pustych wierszy startowo
    can_delete=True,   # możliwość usuwania wierszy
)


class PriceListUploadForm(forms.Form):
    date_start = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    date_end = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    pdf_file = forms.FileField(
        validators=[FileExtensionValidator(allowed_extensions=["pdf"])],
        help_text="Wgraj plik PDF z cennikiem."
    )


class WarehouseStockSellForm(forms.Form):
    customer = forms.ModelChoiceField(queryset=Buyer.objects.all(), required=False, label="Klient")
    customer_alter_name = forms.CharField(max_length=32, required=False, label="Klient (ręcznie)")

    order = forms.ModelChoiceField(queryset=Order.objects.all(), required=False, label="Zlecenie (opcjonalnie)")

    quantity = forms.IntegerField(min_value=1, label="Ilość")
    price = forms.DecimalField(max_digits=12, decimal_places=2, required=True, label="Cena / szt.")
    date = forms.DateField(initial=timezone.now().date, required=True, label="Data")

    def clean(self):
        cd = super().clean()
        customer = cd.get("customer")
        alt = (cd.get("customer_alter_name") or "").strip()

        if not customer and not alt:
            raise ValidationError("Podaj klienta lub wpisz nazwę ręcznie.")

        if customer and alt:
            raise ValidationError("Wybierz klienta ALBO wpisz nazwę ręcznie (nie oba).")

        return cd


class WarehouseStockFifoSellForm(forms.Form):
    customer = forms.ModelChoiceField(queryset=Buyer.objects.all(), required=False, label="Klient")
    customer_alter_name = forms.CharField(max_length=32, required=False, label="Klient (ręcznie)")
    quantity = forms.IntegerField(min_value=1, label="Ilość")
    price = forms.DecimalField(max_digits=12, decimal_places=2, required=True, label="Cena / szt.")
    date = forms.DateField(initial=timezone.now().date, required=True, label="Data")

    def clean(self):
        cd = super().clean()
        customer = cd.get("customer")
        alt = (cd.get("customer_alter_name") or "").strip()

        if not customer and not alt:
            raise ValidationError("Podaj klienta lub wpisz nazwę ręcznie.")
        if customer and alt:
            raise ValidationError("Wybierz klienta ALBO wpisz nazwę ręcznie.")

        return cd



