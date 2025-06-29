from django.forms import ModelForm, TextInput, Select, DateTimeInput, SelectMultiple
from production.models import *
from warehousemanager.models import Person


class ProductionOrderForm(ModelForm):
    class Meta:
        model = ProductionOrder
        # fields = ('id_number', 'cardboard', 'cardboard_dimensions', 'customer', 'dimensions', 'quantity', 'status', 'notes')
        fields = '__all__'


class ProductionUnitForm(ModelForm):
    workers_num = 0

    def __init__(self, day=None, *args, **kwargs):
        super(ProductionUnitForm, self).__init__(*args, **kwargs)
        all_workers = Person.objects.all()
        if day:
            c_workers = Person.objects.filter(job_start__lte=day, job_end__isnull=True)

            all_workers = c_workers

        self.fields['persons'].queryset = all_workers
        workers_num = len(all_workers)

    class Meta:
        size = len(Person.objects.filter(job_start__lte=datetime.datetime.today(), job_end__isnull=True))
        model = ProductionUnit
        fields = '__all__'
        widgets = {
            'start': DateTimeInput(attrs={'type': 'datetime'}),
            'end': DateTimeInput(attrs={'type': 'datetime'}),
            'persons': SelectMultiple(attrs={'size': f'{size}'})
        }


class QuickProductionUnitForm(ModelForm):
    class Meta:
        model = ProductionUnit
        fields = ['work_station', 'estimated_time', 'required_operators', 'required_helpers']
