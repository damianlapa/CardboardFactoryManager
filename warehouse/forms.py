from django.forms import ModelForm, Form, FileField
from warehouse.models import DeliveryItem


class DeliveryItemForm(ModelForm):
    class Meta:
        model = DeliveryItem
        fields = ['delivery', 'order', 'quantity', 'palettes_quantity']
        # fields = '__all__'


class CSVUploadForm(Form):
    file = FileField(label="Plik CSV do importu")
