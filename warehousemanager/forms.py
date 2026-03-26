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
