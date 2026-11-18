from django import forms
from decimal import Decimal


class SheetCalculationForm(forms.Form):
    packaging_type = forms.IntegerField(min_value=1)
    material = forms.IntegerField(min_value=1)

    width = forms.IntegerField(min_value=1)
    length = forms.IntegerField(min_value=1)
    height = forms.IntegerField(min_value=1)

    products_per_sheet = forms.DecimalField(
        min_value=Decimal("0.01"),
        max_digits=8,
        decimal_places=2,
    )
