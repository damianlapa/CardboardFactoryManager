from django import forms
from warehousemanager.models import CardboardProvider


class CardboardProviderForm(forms.Form):
    name = forms.CharField(label='Nazwa producenta', max_length=50, widget=forms.Textarea)

