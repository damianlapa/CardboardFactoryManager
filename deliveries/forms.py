from deliveries.models import *
from django.forms import ModelForm, DateInput


class EventForm(ModelForm):
    class Meta:
        model = Event
        fields = '__all__'
        widgets = {
            'day': DateInput(attrs={'type': 'date'}),
        }