from django.forms import ModelForm, Form, FileField, inlineformset_factory
from warehouse.models import DeliveryItem, Delivery, DeliveryPalette


class DeliveryItemForm(ModelForm):
    class Meta:
        model = DeliveryItem
        fields = ['delivery', 'order', 'quantity', 'palettes_quantity']
        # fields = '__all__'


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
