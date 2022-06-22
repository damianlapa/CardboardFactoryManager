from django.forms import ModelForm, TextInput, Select, DateTimeInput
from production.models import *
from warehousemanager.models import Person


class ProductionOrderForm(ModelForm):
    class Meta:
        model = ProductionOrder
        fields = '__all__'


class ProductionUnitForm(ModelForm):
    class Meta:
        model = ProductionUnit
        fields = '__all__'
        widgets = {
            'start': DateTimeInput(attrs={'type': 'datetime'}),
            'end': DateTimeInput(attrs={'type': 'datetime'}),
        }

    def __init__(self, day=None, *args, **kwargs):
        super(ProductionUnitForm, self).__init__(*args, **kwargs)
        all_workers = Person.objects.all()
        if day:
            print('DATE', day)
            c_workers = Person.objects.filter(job_start__lte=day, job_end__isnull=True)

            all_workers = c_workers

        self.fields['persons'].queryset = all_workers
