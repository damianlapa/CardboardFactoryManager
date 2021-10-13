from django.db import models
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from warehousemanager.models import Person, Buyer, Holiday

import datetime

PRODUCTION_ORDER_STATUSES = (
    ('UNCOMPLETED', 'UNCOMPLETED'),
    ('COMPLETED', 'COMPLETED'),
    ('PLANNED', 'PLANNED'),
    ('FINISHED', 'FINISHED')
)

PRODUCTION_UNIT_STATUSES = (
    ('NOT STARTED', 'NOT STARTED'),
    ('PLANNED', 'PLANNED'),
    ('IN PROGRESS', 'IN PROGRESS'),
    ('FINISHED', 'FINISHED')
)


def add_times_includes_working_hours(date_start, time_delta_in_minutes):
    """
    need a correct with timezone issue
    :param date_start:
    :param time_delta_in_minutes:
    :return:
    """
    date_end = date_start
    hours = time_delta_in_minutes // 60
    minutes = time_delta_in_minutes % 60

    for _ in range(hours):
        date_end += datetime.timedelta(hours=1)
        if date_end.hour == 9:
            date_end += datetime.timedelta(minutes=15)
        if date_end.hour == 13:
            if date_end.isoweekday() >= 5:
                date_end += datetime.timedelta(hours=64)
            else:
                date_end += datetime.timedelta(hours=16)

    for _ in range(minutes // 15):
        date_end += datetime.timedelta(minutes=15)
        if date_end.hour == 9 and 0 <= date_end.minute < 16:
            date_end += datetime.timedelta(minutes=15)

    date_end += datetime.timedelta(minutes=minutes % 15)

    return date_end


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
        return f'{self.id_number} {self.customer} {self.dimensions}'

    def planned_end(self):
        if self.status == 'PLANNED':
            units = ProductionUnit.objects.filter(production_order=self).order_by('-sequence')
            if units[0].estimated_end():
                return units[0].estimated_end()


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

    def first_planned(self):
        units = ProductionUnit.objects.filter(work_station=self, status='PLANNED').order_by('order')
        if units:
            return units[0]
        else:
            return 'NO PLANNED UNITS'

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
        return f'{self.sequence}) {self.work_station} {self.production_order} {self.status}'

    @classmethod
    def last_in_line(cls, station, point=None):
        all_units = cls.objects.filter(order__isnull=False, work_station=station, status='PLANNED').order_by('order')
        if point:
            all_units = all_units.filter(order__lt=point)
        print(all_units)
        return tuple(all_units)[-1].order if all_units.count() > 0 else 0

    @classmethod
    def next_in_line(cls, station, point):
        all_units = cls.objects.filter(order__isnull=False, work_station=station, status='PLANNED',
                                       order__lt=point).order_by('-order')
        return tuple(all_units)[0] if all_units.count() > 0 else False

    @classmethod
    def previous_in_line(cls, station, point):
        all_units = cls.objects.filter(order__isnull=False, work_station=station, status='PLANNED',
                                       order__gt=point).order_by('order')
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
        else:
            try:
                previous_unit = ProductionUnit.objects.get(production_order=self.production_order,
                                                           sequence=self.sequence - 1)
                if previous_unit.estimated_end():
                    if self.estimated_time:
                        if self.start:
                            return self.start + datetime.timedelta(minutes=self.estimated_time)
                return False
            except ObjectDoesNotExist:
                return False

    def move_up_unit(self):
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

    def move_down_unit(self):
        if self.order or self.order == 0:
            if ProductionUnit.previous_in_line(self.work_station, self.order):
                place = ProductionUnit.previous_in_line(self.work_station, self.order).order
                previous_unit = ProductionUnit.objects.get(work_station=self.work_station, order=place)
                previous_unit.order = self.order
                previous_unit.save()
                self.order = place
                self.save()

        else:
            pass

    def previous_unit_end_time(self):
        if self.sequence == 1:
            return False
        if self.sequence > 1:
            try:
                previous_unit = ProductionUnit.objects.get(production_order=self.production_order,
                                                           sequence=self.sequence - 1)
                if previous_unit.planned_end():
                    return previous_unit.planned_end()
                return 'Previous unit has not been planned yet!'
            except ObjectDoesNotExist:
                return 'There is no previous unit, which should exists!'

    def planned_start(self):
        if self.status == 'PLANNED':
            if self.order or self.order == 0:
                if not ProductionUnit.next_in_line(self.work_station, self.order):
                    if ProductionUnit.objects.filter(work_station=self.work_station, status='IN PROGRESS'):
                        units = ProductionUnit.objects.filter(work_station=self.work_station, status='IN PROGRESS')
                        unit_in_progress = units[0]
                        if unit_in_progress.planned_end():
                            return unit_in_progress.planned_end()
                    else:
                        return datetime.datetime.now()
                else:
                    next_in_line = ProductionUnit.next_in_line(self.work_station, self.order)
                    return next_in_line.planned_end()

    def planned_end(self):
        if self.start:
            if self.estimated_time:
                return add_times_includes_working_hours(self.start, self.estimated_time)
        if self.planned_start():
            if self.estimated_time:
                return add_times_includes_working_hours(self.planned_start(), self.estimated_time)

    def unit_duration(self):
        def change_difference_to_time(difference_value):
            hours = difference_value.seconds // 3600
            minutes = (difference_value.seconds // 60) - hours * 60
            seconds = difference_value.seconds - hours * 3600 - minutes * 60

            if minutes < 10:
                minutes = f'0{minutes}'
            if seconds < 10:
                seconds = f'0{seconds}'

            return f'{hours}:{minutes}:{seconds}'

        if self.start and self.end:
            self.start += datetime.timedelta(hours=2)
            self.end += datetime.timedelta(hours=2)
            difference = self.end - self.start
            if self.end.month == self.start.month:
                same_day = self.end.day == self.start.day
                if same_day:
                    '''hours = difference.seconds // 3600
                    minutes = (difference.seconds // 60) - hours * 60
                    seconds = difference.seconds - hours * 3600 - minutes * 60

                    if minutes < 10:
                        minutes = f'0{minutes}'
                    if seconds < 10:
                        seconds = f'0{seconds}'

                    return f'{hours}:{minutes}:{seconds}'''
                    return change_difference_to_time(difference)

                else:
                    if self.end.month == self.start.month:
                        days_difference = self.end.day - self.start.day
                        hours_difference = 0
                        if days_difference <= 4:
                            if self.end.isoweekday > self.start.isoweekday:
                                difference = difference - (16 * days_difference)
                                return change_difference_to_time(difference)
                    else:
                        pass

    def estimated_duration(self):
        if self.estimated_time:

            hours = self.estimated_time // 60
            minutes = self.estimated_time - hours * 60

            if minutes < 10:
                minutes = f'0{minutes}'

            return f'{hours}:{minutes}:00'