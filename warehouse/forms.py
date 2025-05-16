from django.forms import ModelForm
from warehouse.models import DeliveryItem


class DeliveryItemForm(ModelForm):
    class Meta:
        model = DeliveryItem
        fields = ['delivery', 'order', 'quantity', 'palettes_quantity']
        # fields = '__all__'