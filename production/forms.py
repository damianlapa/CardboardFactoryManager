from django.forms import ModelForm, TextInput, Select
from production.models import *


class ProductionOrderForm(ModelForm):
    class Meta:
        model = ProductionOrder
        fields = '__all__'


class ProductionUnitForm(ModelForm):
    class Meta:
        model = ProductionUnit
        fields = '__all__'
