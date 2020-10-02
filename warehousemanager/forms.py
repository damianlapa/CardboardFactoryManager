from django import forms
from warehousemanager.models import CardboardProvider, OrderItem


class CardboardProviderForm(forms.Form):
    name = forms.CharField(label='Nazwa producenta', max_length=50, widget=forms.Textarea)


class NewOrderForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = '__all__'

