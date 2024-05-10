from django.forms import ModelForm, DateInput
from orders.models import *


# class ProductForm(ModelForm):
#     class Meta:
#         model = Product
#         fields = '__all__'


class OrderForm(ModelForm):
    class Meta:
        model = Order
        fields = '__all__'

        widgets = {
            'date': DateInput(format='%d/%m/%Y', attrs={'type': 'date'}),
            'deadline': DateInput(format='%d/%m/%Y', attrs={'type': 'date'}),
        }
