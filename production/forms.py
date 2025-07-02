from django.forms import ModelForm, TextInput, Select, DateTimeInput, SelectMultiple
from production.models import *
from warehousemanager.models import Person


class ProductionOrderForm(ModelForm):
    class Meta:
        model = ProductionOrder
        # fields = ('id_number', 'cardboard', 'cardboard_dimensions', 'customer', 'dimensions', 'quantity', 'status', 'notes')
        fields = '__all__'


class ProductionUnitForm(ModelForm):
    def __init__(self, day=None, *args, **kwargs):
        super(ProductionUnitForm, self).__init__(*args, **kwargs)
        if not day:
            day = datetime.datetime.today()
        c_workers = Person.objects.filter(job_start__lte=day, job_end__isnull=True, occupancy_type__in=("PRODUCTION", "LOGISTIC"))

        self.fields['persons'].widget.attrs['size'] = str(c_workers.count())
        self.fields['persons'].queryset = c_workers

    class Meta:
        model = ProductionUnit
        fields = '__all__'
        widgets = {
            'start': DateTimeInput(attrs={'type': 'datetime'}),
            'end': DateTimeInput(attrs={'type': 'datetime'}),
            'persons': SelectMultiple()
        }


class QuickProductionUnitForm(ModelForm):
    class Meta:
        model = ProductionUnit
        fields = ['work_station', 'estimated_time', 'required_operators', 'required_helpers']
