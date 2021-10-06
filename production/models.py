from django.db import models
from warehousemanager.models import Person, Buyer

import datetime

PRODUCTION_ORDER_STATUSES = (
    ('UNCOMPLETED', 'UNCOMPLETED'),
    ('PLANNED', 'PLANNED'),
    ('COMPLETED', 'COMPLETED')
)

PRODUCTION_UNIT_STATUSES = (
    ('NOT STARTED', 'NOT STARTED'),
    ('PLANNED', 'PLANNED'),
    ('IN PROGRESS', 'IN PROGRESS'),
    ('FINISHED', 'FINISHED')
)


class ProductionOrder(models.Model):
    id_number = models.CharField(max_length=32, unique=True)
    cardboard = models.CharField(max_length=32, blank=True)
    cardboard_dimensions = models.CharField(max_length=32, blank=True)
    customer = models.ForeignKey(Buyer, on_delete=models.CASCADE)
    dimensions = models.CharField(max_length=32, null=True, blank=True)
    quantity = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=32, choices=PRODUCTION_ORDER_STATUSES, default='UNCOMPLETED')
    completed = models.DateTimeField(null=True, blank=True)
    priority = models.BooleanField(default=False)
    notes = models.CharField(max_length=1000, null=True, blank=True)

    def __str__(self):
        return f'{self.id_number} {self.customer} {self.dimensions} [{self.status}]'


class WorkStation(models.Model):
    name = models.CharField(max_length=48)

    def __str__(self):
        return self.name


class ProductionUnit(models.Model):
    production_order = models.ForeignKey(ProductionOrder, on_delete=models.CASCADE)
    work_station = models.ForeignKey(WorkStation, on_delete=models.CASCADE)
    order = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=32, choices=PRODUCTION_UNIT_STATUSES, default='NOT STARTED')
    persons = models.ManyToManyField(Person)
    estimated_time = models.IntegerField(null=True, blank=True)
    start = models.DateTimeField(null=True, blank=True)
    end = models.DateTimeField(null=True, blank=True)
    quantity_start = models.IntegerField(null=True, blank=True)
    quantity_end = models.IntegerField(null=True, blank=True)
    notes = models.CharField(max_length=1000, null=True, blank=True)

    def __str__(self):
        return f'{self.work_station} {self.production_order} {self.status}'

    def estimated_end(self):
        if self.start:
            if self.estimated_time:
                return self.start + datetime.timedelta(minutes=self.estimated_time)

