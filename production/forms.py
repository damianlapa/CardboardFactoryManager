from django.forms import ModelForm, TextInput, Select, DateTimeInput
from production.models import *


class ProductionOrderForm(ModelForm):
    class Meta:
        model = ProductionOrder
        fields = '__all__'


class ProductionUnitForm(ModelForm):
    class Meta:
        model = ProductionUnit
        fields = '__all__'
        widgets = {
            'start': DateTimeInput(attrs={'type': 'datetime'}),
            'end': DateTimeInput(attrs={'type': 'datetime'}),
        }
