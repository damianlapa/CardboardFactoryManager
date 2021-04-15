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


class DeliveryForm(forms.ModelForm):
    class Meta:
        model = Delivery
        fields = ('provider', 'date_of_delivery')

        widgets = {
            'date_of_delivery': forms.DateInput(format='%d/%m/%Y', attrs={'type': 'date'})
        }


class OrderItemQuantityForm(forms.ModelForm):
    class Meta:
        model = OrderItemQuantity
        fields = ('delivery', 'order_item', 'quantity')

    def __init__(self, provider=None, *args, **kwargs):
        super(OrderItemQuantityForm, self).__init__(*args, **kwargs)
        uncompleted_items = []
        if provider:
            all_items = OrderItem.objects.filter(order__provider=provider)
            uncompleted_items = all_items.filter(is_completed=False).order_by('order__order_item_number', 'item_number')

        self.fields['order_item'].queryset = uncompleted_items


class PaletteQuantityForm(forms.ModelForm):
    class Meta:
        model = PaletteQuantity
        fields = ('delivery', 'palette', 'quantity', 'status')


class ExtraHoursForm(forms.ModelForm):
    class Meta:
        model = ExtraHour
        fields = '__all__'

        widgets = {
            'extras_date': forms.DateInput(format='%d/%m/%Y', attrs={'type': 'date'}),
        }


class PolymerForm(forms.ModelForm):
    class Meta:
        model = Photopolymer
        fields = '__all__'


class PasswordForm(forms.Form):
    new_password = forms.CharField(label='New Password', max_length=32, widget=forms.PasswordInput)
    repeated_password = forms.CharField(label='Repeated Password', max_length=32, widget=forms.PasswordInput)
    old_password = forms.CharField(label='Old Password', max_length=32, widget=forms.PasswordInput)


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ('recipient', 'title', 'content')