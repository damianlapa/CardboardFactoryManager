from django import forms
from warehousemanager.models import *


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


class WorkReminderForm(forms.ModelForm):
    class Meta:
        model = WorkReminder
        fields = '__all__'


class GluerNumberForm(forms.ModelForm):
    class Meta:
        model = GluerNumber
        fields = "__all__"


from django import forms


class PersonPinForm(forms.Form):
    current_pin = forms.CharField(
        label="Obecny PIN",
        required=False,
        widget=forms.PasswordInput(
            attrs={
                "inputmode": "numeric",
                "autocomplete": "off",
                "placeholder": "Obecny PIN",
            }
        ),
    )

    new_pin = forms.CharField(
        label="Nowy PIN",
        widget=forms.PasswordInput(
            attrs={
                "inputmode": "numeric",
                "autocomplete": "new-password",
                "placeholder": "Nowy PIN",
            }
        ),
    )

    new_pin_repeat = forms.CharField(
        label="Powtórz nowy PIN",
        widget=forms.PasswordInput(
            attrs={
                "inputmode": "numeric",
                "autocomplete": "new-password",
                "placeholder": "Powtórz nowy PIN",
            }
        ),
    )

    def clean_new_pin(self):
        pin = str(self.cleaned_data["new_pin"]).strip()

        if not pin.isdigit():
            raise forms.ValidationError("PIN może zawierać tylko cyfry.")

        if len(pin) < 4:
            raise forms.ValidationError("PIN musi mieć co najmniej 4 cyfry.")

        if len(pin) > 8:
            raise forms.ValidationError("PIN może mieć maksymalnie 8 cyfr.")

        return pin

    def clean(self):
        cleaned_data = super().clean()

        new_pin = cleaned_data.get("new_pin")
        new_pin_repeat = cleaned_data.get("new_pin_repeat")

        if new_pin and new_pin_repeat and new_pin != new_pin_repeat:
            self.add_error(
                "new_pin_repeat",
                "Podane nowe PIN-y nie są identyczne.",
            )

        return cleaned_data


from django import forms

from warehousemanager.models import (
    Photopolymer,
)


class PolymerForm(forms.ModelForm):

    class Meta:
        model = Photopolymer

        fields = [
            "producer",
            "identification_number",
            "identification_letter",
            "customer",
            "name",
            "dimensions",
            "colors",
            "delivery_date",
            "project",
            "link",
            "active",
        ]

        widgets = {
            "delivery_date": forms.DateInput(
                attrs={
                    "type": "date",
                }
            ),
        }


class PolymerServiceForm(forms.ModelForm):

    class Meta:
        model = PhotopolymerService

        fields = [
            "photopolymer",
            "send_date",
            "company",
            "service_description",
            "return_date",
        ]

        widgets = {
            "send_date": forms.DateInput(
                attrs={
                    "type": "date",
                }
            ),
            "return_date": forms.DateInput(
                attrs={
                    "type": "date",
                }
            ),
            "service_description": forms.Textarea(
                attrs={
                    "rows": 4,
                }
            ),
        }

        labels = {
            "photopolymer": "Polimer",
            "send_date": "Data wysłania",
            "company": "Firma / kurier",
            "service_description": "Opis wysyłki / serwisu",
            "return_date": "Data zwrotu",
        }

    def clean(self):
        cleaned_data = super().clean()

        send_date = cleaned_data.get(
            "send_date"
        )

        return_date = cleaned_data.get(
            "return_date"
        )

        if (
            send_date
            and return_date
            and return_date < send_date
        ):
            self.add_error(
                "return_date",
                "Data zwrotu nie może być wcześniejsza niż data wysłania.",
            )

        return cleaned_data


from django import forms
from django.forms import inlineformset_factory

from .models import ColorOrder, ColorOrderItem


class ColorOrderForm(forms.ModelForm):
    class Meta:
        model = ColorOrder
        fields = [
            "provider",
            "order_date",
            "number",
            "notes",
        ]

        widgets = {
            "provider": forms.Select(),
            "order_date": forms.DateInput(
                attrs={
                    "type": "date",
                }
            ),
            "number": forms.TextInput(),
            "notes": forms.Textarea(
                attrs={
                    "rows": 3,
                }
            ),
        }


class ColorOrderItemForm(forms.ModelForm):
    class Meta:
        model = ColorOrderItem
        fields = [
            "color",
            "quantity_kg",
            "price_per_kg",
        ]

        widgets = {
            "color": forms.Select(),
            "quantity_kg": forms.NumberInput(
                attrs={
                    "step": "0.01",
                    "min": "0.01",
                }
            ),
            "price_per_kg": forms.NumberInput(
                attrs={
                    "step": "0.01",
                    "min": "0",
                }
            ),
        }

    def clean_quantity_kg(self):
        value = self.cleaned_data["quantity_kg"]

        if value <= 0:
            raise forms.ValidationError(
                "Ilość musi być większa od 0 kg."
            )

        return value

    def clean_price_per_kg(self):
        value = self.cleaned_data["price_per_kg"]

        if value < 0:
            raise forms.ValidationError(
                "Cena nie może być ujemna."
            )

        return value


ColorOrderItemFormSet = inlineformset_factory(
    ColorOrder,
    ColorOrderItem,
    form=ColorOrderItemForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,
)