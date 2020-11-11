from django import forms
from warehousemanager.models import *


class CardboardProviderForm(forms.ModelForm):
    class Meta:
        model = CardboardProvider
        fields = ('name',)


class NewOrderItemForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = '__all__'


class NewOrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ('provider', 'order_provider_number', 'date_of_order')


class NoteForm(forms.ModelForm):
    class Meta:
        model = Note
        fields = '__all__'


class AbsenceForm(forms.ModelForm):
    class Meta:
        model = Absence
        fields = '__all__'

        widgets = {
            'absence_date': forms.DateInput(format='%d/%m/%Y', attrs={'type': 'date'}),
        }


class PunchForm(forms.ModelForm):
    class Meta:
        model = Punch
        fields = '__all__'


class BuyerForm(forms.ModelForm):
    class Meta:
        model = Buyer
        fields = '__all__'


class PunchProductionForm(forms.ModelForm):
    class Meta:
        model = PunchProduction
        fields = '__all__'

        widgets = {
            'date_end': forms.DateInput(format='%d/%m/%Y', attrs={'type': 'date'}),
            'date_start': forms.DateInput(format='%d/%m/%Y', attrs={'type': 'date'}),
        }
