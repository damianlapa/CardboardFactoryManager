from django import forms
from warehousemanager.models import CardboardProvider, OrderItem, Order, Note, Absence


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
