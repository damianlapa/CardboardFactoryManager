from django.forms import ModelForm, Form, FileField, inlineformset_factory, BaseInlineFormSet
from warehouse.models import Product, DeliverySpecialItem, DeliveryItem, Delivery, DeliveryPalette, ProductSell2, ProductComplexAssembly, ProductComplexParts, WarehouseStock
from django import forms


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


class ProductSell2Form(ModelForm):
    class Meta:
        model = ProductSell2
        fields = ['product', 'quantity', 'price', 'date']



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

