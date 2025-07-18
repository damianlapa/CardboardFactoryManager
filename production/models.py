from django.db import models
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from warehousemanager.models import Person, Buyer, Holiday, Punch, Photopolymer

import datetime

PRODUCTION_ORDER_STATUSES = (
    ('ORDERED', 'ORDERED'),
    ('UNCOMPLETED', 'UNCOMPLETED'),
    ('COMPLETED', 'COMPLETED'),
    ('PLANNED', 'PLANNED'),
    ('FINISHED', 'FINISHED'),
    ('ARCHIVED', 'ARCHIVED')
)

PRODUCTION_UNIT_STATUSES = (
    ('FINISHED', 'FINISHED'),
    ('NOT STARTED', 'NOT STARTED'),
    ('PLANNED', 'PLANNED'),
    ('IN PROGRESS', 'IN PROGRESS'),
)


def add_times_includes_working_hours(date_start, time_delta_in_minutes):
    from warehousemanager.models import Holiday
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
        timezone_factor = 2 if str(date_start.tzinfo) == 'UTC' else 0
        date_end += datetime.timedelta(hours=1)
        if date_end.hour == 11 - timezone_factor:
            date_end += datetime.timedelta(minutes=15)
        if date_end.hour == 15 - timezone_factor:
            if date_end.isoweekday() >= 5:
                date_end += datetime.timedelta(hours=64)
            else:
                date_end += datetime.timedelta(hours=16)
        if len(Holiday.objects.filter(holiday_date=date_end.date())) > 0:
            date_end += datetime.timedelta(hours=24)

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
    ordered_quantity = models.PositiveIntegerField(null=True, blank=True)
    quantity = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=32, choices=PRODUCTION_ORDER_STATUSES, default='UNCOMPLETED')
    completed = models.DateTimeField(null=True, blank=True)
    priority = models.BooleanField(default=False)
    notes = models.CharField(max_length=1000, null=True, blank=True)
    add_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.id_number} {self.customer} {self.dimensions}'

    def planned_end(self):
        if self.status == 'PLANNED':
            units = ProductionUnit.objects.filter(production_order=self).order_by('-sequence')
            if units[0].planned_end():
                return units[0].planned_end()

    def cardboard_layers(self):
        if self.cardboard:
            layers = 0
            for letter in self.cardboard:
                if letter.isdigit():
                    layers = int(letter)
                    break
            return layers
        return None

    def cardboard_area(self):
        cardboard_area = None
        cardboard_dimensions = [] if not self.cardboard_dimensions else self.cardboard_dimensions.lower().split('x')
        try:
            cardboard_dimensions = [int(dimension) for dimension in cardboard_dimensions]
        except Exception:
            cardboard_dimensions = []

        if cardboard_dimensions:
            try:
                cardboard_area = cardboard_dimensions[0] * cardboard_dimensions[1] / 1000000
                cardboard_area = round(cardboard_area, 2)
            except Exception:
                cardboard_area = 0

        return cardboard_area

    class Meta:
        ordering = ['add_date']


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

    def workstation_occupancy(self, start, end):
        all_units = ProductionUnit.objects.filter(work_station=self, end__gte=start, end__lte=end)

        def work_hours_between_dates(date_start, date_end):
            date_end = date_end + datetime.timedelta(days=1)
            from warehousemanager.models import Holiday
            holidays = Holiday.objects.filter(holiday_date__gte=start, holiday_date__lte=end)
            holidays_num = 0
            for h in holidays:
                if h.holiday_date.isoweekday() < 5:
                    holidays_num += 1
            difference = (date_end - date_start) - datetime.timedelta(hours=holidays_num * 8)
            days_difference = int(date_end.strftime('%j')) - int(date_start.strftime('%j'))
            difference = difference - datetime.timedelta(hours=days_difference * 16)
            weekends = end.isocalendar()[1] - start.isocalendar()[1]
            difference = difference - datetime.timedelta(hours=weekends * 16)

            return difference

        return work_hours_between_dates(start, end)

    def workstation_occupancy_during_day(self, day):
        results = ProductionUnit.workstation_occupancy_during_day(day)
        results_by_workstation = [[] for _ in range(4)]
        for num in range(results):
            for unit in results[num]:
                if unit.workstation == self:
                    results_by_workstation[num].append(unit)

        if results_by_workstation[1]:
            return 1
        return 0

    def oee_factor(self, year, month, dates=None):
        if not dates:
            start = datetime.date(year, month, 1)
            month = month + 1 if month != 12 else 1
            end = datetime.date(year, month, 1) - datetime.timedelta(days=1)
        else:
            start, end = dates.split('x')
            sy, sm, sd = list(map(int, start.split('-')))
            ey, em, ed = list(map(int, end.split('-')))
            start = datetime.date(sy, sm, sd)
            end = datetime.date(ey, em, ed)

        teep_time = (end - start).days * 24 * 60

        units = ProductionUnit.objects.filter(work_station=self, start__gte=start, end__lte=end)

        minutes = 0
        operation_time = 0
        planned_time = 0
        pieces_ok = 0
        pieces_nok = 0

        while start <= end:
            holiday = Holiday.objects.filter(holiday_date=start)
            if start.isoweekday() <= 5 and not holiday:
                if start.isoweekday() == 5:
                    minutes += 385
                else:
                    minutes += 445
            start += datetime.timedelta(days=1)

        for unit in units:
            time = unit.unit_duration2()
            unit_planned_time = unit.estimated_time
            unit_q_end = unit.quantity_end
            unit_q_start = unit.quantity_start
            if unit_q_start and unit_q_end:
                pieces_ok += unit_q_end
                pieces_nok += unit_q_start - unit_q_end
            elif unit_q_end:
                pieces_ok += unit_q_end
                pieces_nok += 0
            planned_time += unit_planned_time if unit_planned_time else 0
            operation_time += time if time else 0

        availability = round((operation_time // 60) / minutes , 3) if minutes else 1
        efficiency = round(planned_time / (operation_time // 60) , 3) if operation_time // 60 != 0 else 1
        quality = round(pieces_ok / (pieces_nok + pieces_ok), 3) if pieces_nok else 1

        teep = minutes / teep_time

        return availability, efficiency, quality, round(availability * efficiency * quality, 3), teep


class ProductionUnit(models.Model):
    production_order = models.ForeignKey(ProductionOrder, on_delete=models.CASCADE)
    sequence = models.IntegerField(default=1)
    work_station = models.ForeignKey(WorkStation, on_delete=models.CASCADE)
    punch = models.ForeignKey(Punch, on_delete=models.PROTECT, blank=True, null=True)
    polymer = models.ForeignKey(Photopolymer, on_delete=models.PROTECT, blank=True, null=True)
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
                if previous_unit.end:
                    return previous_unit.end
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
                        if datetime.datetime.now().isoweekday() >= 6:
                            days_difference = 8 - datetime.datetime.now().isoweekday()
                            day = datetime.datetime.now().date() + datetime.timedelta(days=days_difference)
                            day_date = datetime.datetime.strptime(f'{day.year}-{day.month}-{day.day} 7:00:00',
                                                                  '%Y-%m-%d %H:%M:%S')
                            return day_date
                        if datetime.datetime.now().hour > 14:
                            if datetime.datetime.now().isoweekday() < 5:
                                day = datetime.datetime.now().date() + datetime.timedelta(days=1)
                                day_date = datetime.datetime.strptime(f'{day.year}-{day.month}-{day.day} 7:00:00',
                                                                      '%Y-%m-%d %H:%M:%S')
                                return day_date
                            else:
                                days_difference = 8 - datetime.datetime.now().isoweekday()
                                day = datetime.datetime.now().date() + datetime.timedelta(days=days_difference)
                                day_date = datetime.datetime.strptime(f'{day.year}-{day.month}-{day.day} 7:00:00',
                                                                      '%Y-%m-%d %H:%M:%S')
                                return day_date
                        elif datetime.datetime.now().hour < 7:
                            if datetime.datetime.now().isoweekday() <= 5:
                                day = datetime.datetime.now().date()
                                day_date = datetime.datetime.strptime(f'{day.year}-{day.month}-{day.day} 7:00:00',
                                                                      '%Y-%m-%d %H:%M:%S')
                                return day_date

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
            days = difference_value.days
            hours = difference_value.seconds // 3600

            minutes = (difference_value.seconds // 60) - hours * 60
            seconds = difference_value.seconds - hours * 3600 - minutes * 60

            if minutes < 10:
                minutes = f'0{minutes}'
            if seconds < 10:
                seconds = f'0{seconds}'

            if days:
                hours += days * 24

            return f'{hours}:{minutes}:{seconds}'

        def holiday_between_days(first_date, second_date):
            holidays = 0
            if second_date.date() > first_date.date():
                while first_date.date() != second_date.date():
                    first_date = first_date + datetime.timedelta(days=1)
                    if len(Holiday.objects.filter(holiday_date=first_date)) > 0:
                        holidays += 1
                return holidays
            else:
                return 0

        if self.start and self.end:
            self.start += datetime.timedelta(hours=2)
            self.end += datetime.timedelta(hours=2)
            print(self.start, self.end)
            difference = self.end - self.start
            if self.end.month == self.start.month:
                same_day = self.end.day == self.start.day
                if same_day:
                    if self.end > datetime.datetime(self.end.year, self.end.month, self.end.day, 11, 0,
                                                    0) + datetime.timedelta(hours=2) > self.start:
                        difference -= datetime.timedelta(minutes=20)
                    return change_difference_to_time(difference)

                else:
                    holidays_to_count = holiday_between_days(self.start, self.end)
                    if self.end.month == self.start.month:
                        days_difference = self.end.day - self.start.day
                        if days_difference <= 4:
                            # the same week
                            if self.end.isoweekday() > self.start.isoweekday():
                                difference = difference - datetime.timedelta(hours=16 * days_difference)
                                if self.start.hour < 11:
                                    if self.end.hour < 11:
                                        difference -= datetime.timedelta(minutes=20 * days_difference)
                                    else:
                                        difference -= datetime.timedelta(minutes=20 * (days_difference + 1))
                            # ends next week
                            else:
                                difference = difference - datetime.timedelta(hours=(days_difference - 2) * 16)
                                difference -= datetime.timedelta(days=2)
                            difference = difference - holidays_to_count * datetime.timedelta(hours=8)
                            return change_difference_to_time(difference)
                        else:
                            # old way
                            day_number = 8 - self.start.isoweekday()
                            full_weeks = (day_number + days_difference) // 7

                            # new way
                            start_day_day_of_week = self.start.isoweekday()
                            end_day_day_of_week = self.end.isoweekday()
                            difference_in_days_between_dates = (self.end - self.start).days
                            weekends = 0

                            if end_day_day_of_week < start_day_day_of_week:
                                weekends += 1
                            weekends += difference_in_days_between_dates // 7

                            if weekends > 0:
                                difference = difference - datetime.timedelta(days=weekends * 2)
                                difference = datetime.timedelta(hours=difference.days * 8) + datetime.timedelta(
                                    seconds=difference.seconds)
                                difference = difference - holidays_to_count * datetime.timedelta(hours=8)
                                return change_difference_to_time(difference)
                            else:
                                difference = difference - holidays_to_count * datetime.timedelta(hours=8)
                                return change_difference_to_time(difference)

                        break_minutes = 0
                        start_day = self.start
                    else:
                        '''
                        TO DO
                        '''
                        pass

            else:
                holidays_during_period = holiday_between_days(self.start, self.end)
                difference = difference - datetime.timedelta(hours=holidays_during_period * 8)
                days_difference = int(self.end.strftime('%j')) - int(self.start.strftime('%j'))
                if self.start.isocalendar()[1] == self.end.isocalendar()[1]:
                    difference = difference - datetime.timedelta(hours=days_difference * 16)
                    return change_difference_to_time(difference)
                else:
                    difference = difference - datetime.timedelta(hours=days_difference * 16)
                    weekends = self.end.isocalendar()[1] - self.start.isocalendar()[1]
                    difference = difference - datetime.timedelta(hours=weekends * 16)
                    return change_difference_to_time(difference)

        else:
            return 'N/D'

    def unit_duration2(self):
        start = self.start
        end = self.end

        if start and end:
            holidays = Holiday.objects.filter(holiday_date__lte=end, holiday_date__gte=start)
            # error handling when start is later than end
            if start > end:
                return None
            # correct times for start and end
            else:
                base = 0
                # same day - WORKS
                if start.date() == end.date():
                    result = (end - start).seconds // 60
                    if start.time().hour < 11 and ((end.time().hour == 11 and end.time().minute >= 20) or end.time().hour > 11):
                        result -= 20
                    return result * 60
                # different days - WORKS
                else:
                    # same week - WORKS
                    if start.isocalendar()[1] == end.isocalendar()[1]:
                        # start time <= end time // base counting - WORKS
                        if start.time() <= end.time():
                            base = ((end - start).seconds + (end - start).days * 8 * 60 * 60) // 60
                        # start time > end time // base counting - WORKS
                        else:
                            base = (((end - start).days + 1) * 8 * 60 * 60 - (start - end).seconds) // 60
                    # different week - WORKS
                    else:
                        # start time <= end time // base counting - WORKS
                        if start.time() <= end.time():
                            base = ((end - start).seconds + ((end - start).days - 2) * 8 * 60 * 60) // 60
                        # start time > end time // base counting - WORKS
                        else:
                            base = (((end - start).days - 1) * 8 * 60 * 60 - (start - end).seconds) // 60

                    # breaks counting - minutes to subtract
                    # start time <= end time
                        # start before 11 and end 11+ // same day - WORKS // same week - WORKS // different week - WORKS
                    if start.time().hour < 11 and end.time().hour >= 11:
                        base -= (end - start).days * 20 + 20
                    elif start.time().hour >= 11 and end.time().hour >= 11 or start.time().hour <= 11 and end.time().hour <= 11:
                        base -= (end - start).days * 20
                    elif start.time().hour >= 11 and end.time().hour <= 11:
                        base -= ((end - start).days) * 20
                    weeks = end.isocalendar()[1] - start.isocalendar()[1]
                    base += weeks * 2 * 20
                    base -= (len(holidays) * 8 * 60) - len(holidays) * 20
                    return base * 60

        else:
            return None

    def duration_in_minutes(self):
        if self.unit_duration2():
            return self.unit_duration2() // 60
        else:
            return None

    def estimated_duration(self):
        if self.estimated_time:

            hours = self.estimated_time // 60
            minutes = self.estimated_time - hours * 60

            if minutes < 10:
                minutes = f'0{minutes}'

            return f'{hours}:{minutes}:00'

    def time_group(self):
        if self.end:
            if datetime.datetime.today().date() == self.end.date():
                return 'today last7 thismonth alltime'
            elif datetime.datetime.today().date() >= self.end.date() > datetime.datetime.today().date() - datetime.timedelta(
                    days=7):
                return 'last7 thismonth alltime'
            elif self.end.date().month == datetime.datetime.today().date().month and self.end.date().year == datetime.datetime.today().date().year:
                return 'thismonth alltime'
            else:
                return 'alltime'

    def unit_duration_in_seconds(self):

        def change_difference_to_time(difference_value):
            days = difference_value.days
            seconds = difference_value.seconds
            if days:
                seconds += days * 3600 * 24

            return seconds

        def holiday_between_days(first_date, second_date):
            holidays = 0
            if second_date.date() > first_date.date():
                while first_date.date() != second_date.date():
                    first_date = first_date + datetime.timedelta(days=1)
                    if len(Holiday.objects.filter(holiday_date=first_date)) > 0:
                        holidays += 1
                return holidays

        if self.start and self.end:
            holidays_to_count = holiday_between_days(self.start, self.end)
            # self.start += datetime.timedelta(hours=2)
            # self.end += datetime.timedelta(hours=2)
            difference = self.end - self.start
            if self.end.month == self.start.month:
                same_day = self.end.day == self.start.day
                if same_day:
                    return change_difference_to_time(difference)

                else:
                    if self.end.month == self.start.month:
                        days_difference = self.end.day - self.start.day

                        if days_difference <= 4:
                            # the same week
                            if self.end.isoweekday() > self.start.isoweekday():
                                difference = difference - datetime.timedelta(hours=16 * days_difference)
                            # ends next week
                            else:
                                difference = difference - datetime.timedelta(hours=(days_difference - 2) * 16)
                                difference -= datetime.timedelta(days=2)
                            difference = difference - holidays_to_count * datetime.timedelta(hours=8)
                            return change_difference_to_time(difference)
                        else:
                            start_day_day_of_week = self.start.isoweekday()
                            end_day_day_of_week = self.end.isoweekday()
                            difference_in_days_between_dates = (self.end - self.start).days
                            weekends = 0

                            if end_day_day_of_week < start_day_day_of_week:
                                weekends += 1
                            weekends += difference_in_days_between_dates // 7
                            if weekends > 0:
                                difference = difference - datetime.timedelta(days=weekends * 2)
                                difference = datetime.timedelta(hours=difference.days * 8) + datetime.timedelta(
                                    seconds=difference.seconds)
                                difference = difference - holidays_to_count * datetime.timedelta(hours=8)
                                return change_difference_to_time(difference)
                            else:
                                difference = difference - holidays_to_count * datetime.timedelta(hours=8)
                                return change_difference_to_time(difference)
                    else:
                        '''
                        TO DO
                        '''
                        pass

    def estimated_duration_in_seconds(self):
        return self.estimated_time * 60 if self.estimated_time else None

    def suggested_time(self):
        quantity = self.quantity_end if self.quantity_end else self.production_order.quantity
        quantity = 0 if not quantity else quantity
        layers = self.production_order.cardboard_layers()
        if self.work_station.name == 'SKLEJARKA':
            if quantity:
                if layers == 3:
                    time_value = int((quantity / 1200) * 60 + 20)
                elif layers == 5:
                    time_value = int((quantity / 600) * 60 + 20)
                else:
                    time_value = None
                return time_value
        elif self.work_station.name == 'ROTACJA':
            dimensions = self.production_order.dimensions.lower().split('x')
            try:
                dimensions = [int(dimension) for dimension in dimensions]
            except Exception:
                dimensions = []
            if len(dimensions) == 3:
                if quantity:
                    base_value = int(quantity * 60 / 4500) if layers == 3 else int(quantity * 60 / 2000)
                    setup = 30
                    if dimensions[0] < 160 or dimensions[1] < 160:
                        base_value = base_value * 2
                        setup += 10
                    if dimensions[2] >= 750:
                        setup += 20

                    if self.production_order.cardboard_dimensions:
                        try:
                            cardboard_dimensions = [int(dimension) for dimension in
                                                    self.production_order.cardboard_dimensions.lower().split('x')]
                        except ValueError:
                            cardboard_dimensions = None
                        if cardboard_dimensions:
                            if cardboard_dimensions[0] > 2268:
                                base_value *= 1.5
                            elif cardboard_dimensions[0] < 500:
                                base_value *= 1.2

                    if self.punch:
                        base_value *= 2
                        setup += 30
                    if self.polymer:
                        base_value *= 1.5
                        setup += 30

                    if self.production_order.cardboard_area():
                        area = self.production_order.cardboard_area()
                        if area > 2:
                            area = 2
                        elif area < 0.5:
                            area = 0.5

                        base_value *= area

                    return int(base_value + setup)
            return None

        elif self.work_station.name == 'TYGIEL MAŁY':
            setup_value = 15
            base_value = 0
            if quantity:
                base_value = int(quantity * 60 / 550) if layers == 3 else int(quantity * 60 / 450)
            return setup_value + base_value

        elif self.work_station.name == 'TYGIEL DUŻY':
            setup_value = 15
            base_value = 0
            if quantity:
                base_value = int(quantity * 60 / 450) if layers == 3 else int(quantity * 60 / 400)

            if self.production_order.cardboard_dimensions:
                try:
                    cardboard_dimensions = [int(dimension) for dimension in
                                            self.production_order.cardboard_dimensions.lower().split('x')]
                except ValueError:
                    cardboard_dimensions = None
                if cardboard_dimensions:
                    if cardboard_dimensions[0] > 1200:
                        base_value *= 1.1
                    if cardboard_dimensions[1] > 800:
                        base_value *= 1.1

            return setup_value + base_value

        return None

    @classmethod
    def worker_occupancy(cls, worker):
        activity = cls.objects.filter(status='IN PROGRESS', persons__in=[worker])
        if activity:
            return activity[0].work_station
        return 'Free'

    @classmethod
    def units_duration_during_day_at_specified_workstation(cls, day, workstation):
        day_start = datetime.datetime.strptime(f'{day} 06:00:00', '%Y-%m-%d %H:%M:%S')
        day_end = datetime.datetime.strptime(f'{day} 16:00:00', '%Y-%m-%d %H:%M:%S')

        result = 0

        units_started_and_finished_during_day = cls.objects.filter(start__gte=day_start, end__lte=day_end,
                                                                   workstation=workstation)
        units_started_before_and_ended_today = cls.objects.filter(start__lt=day_start, end__gte=day_start,
                                                                  workstation=workstation)
        units_started_today_and_not_finished = cls.objects.filter(start__lte=day_end, end__gt=day_end,
                                                                  workstation=workstation)
        units_started_earlier_and_not_finished = cls.objects.filter(start__lt=day_start, end__gt=day_end,
                                                                    workstation=workstation)

        for u in units_started_and_finished_during_day:
            result += u.unit_duration_in_seconds()
        pass

        return [units_started_and_finished_during_day, units_started_earlier_and_not_finished,
                units_started_before_and_ended_today, units_started_today_and_not_finished]
