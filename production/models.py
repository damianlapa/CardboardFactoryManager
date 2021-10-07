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

    def currently_in_production(self):
        units = ProductionUnit.objects.filter(work_station=self, status='IN PROGRESS')
        if units:
            if units.count() > 1:
                return 'MORE THAN ONE IN PROGRESS'
            else:
                return units[0]
        return 'UNOCCUPIED'


class ProductionUnit(models.Model):
    production_order = models.ForeignKey(ProductionOrder, on_delete=models.CASCADE)
    sequence = models.IntegerField(default=1)
    work_station = models.ForeignKey(WorkStation, on_delete=models.CASCADE)
    order = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=32, choices=PRODUCTION_UNIT_STATUSES, default='NOT STARTED')
    persons = models.ManyToManyField(Person, blank=True)
    estimated_time = models.IntegerField(null=True, blank=True)
    start = models.DateTimeField(null=True, blank=True)
    end = models.DateTimeField(null=True, blank=True)
    quantity_start = models.IntegerField(null=True, blank=True)
    quantity_end = models.IntegerField(null=True, blank=True)
    notes = models.CharField(max_length=1000, null=True, blank=True)

    def __str__(self):
        return f'{self.work_station} {self.production_order} {self.status}'

    @classmethod
    def last_in_line(cls, station, point=None):
        all_units = cls.objects.filter(order__isnull=False, work_station=station).order_by('order')
        if point:
            all_units = all_units.filter(order__lt=point)
        return tuple(all_units)[-1].order if all_units.count() > 0 else 0

    @classmethod
    def next_in_line(cls, station, point):
        all_units = cls.objects.filter(order__isnull=False, work_station=station, order__gt=point).order_by('order')
        return tuple(all_units)[0] if all_units.count() > 0 else False

    @classmethod
    def shift_units(cls, station, point):
        all_units = cls.objects.filter(order__isnull=False, work_station=station, order__gte=point).order_by('-order')
        for unit in all_units:
            unit.order += 1
            unit.save()

    def estimated_end(self):
        all_order_steps = ProductionUnit.objects.filter(production_order=self.production_order)
        if self.sequence == 1:
            if self.start:
                if self.estimated_time:
                    return self.start + datetime.timedelta(minutes=self.estimated_time)

    def move_up_order(self):
        if self.order or self.order == 0:
            if self.order > 0:
                place = ProductionUnit.last_in_line(self.work_station, self.order)
                ProductionUnit.shift_units(self.work_station, place)
                self.order = place
                self.save()
        else:
            place = ProductionUnit.last_in_line(self.work_station)
            ProductionUnit.shift_units(self.work_station, place)
            self.order = place
            self.save()

    def move_down_order(self):
        pass
        '''if self.order or self.order == 0:
            if ProductionUnit.next_in_line(self.work_station, self.order):
                place = ProductionUnit.last_in_line(self.work_station, self.order)
                ProductionUnit.shift_units(self.work_station, place)
                self.order = place
                self.save()
        else:
            place = ProductionUnit.last_in_line(self.work_station)
            ProductionUnit.shift_units(self.work_station, place)
            self.order = place
            self.save()'''

    def check_realization_possibility(self):
        if self.order:
            planned_units = ProductionUnit.objects.filter(work_station=self.work_station)
