from django.db import models
from django.db.models.functions import ExtractYear
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import User
from django.urls import reverse
import decimal
import datetime
from warehousemanager.clear_funcs import work_days_during_period

MONTHS = (
    ('1', 'January'),
    ('2', 'February'),
    ('3', 'March'),
    ('4', 'April'),
    ('5', 'May'),
    ('6', 'June'),
    ('7', 'July'),
    ('8', 'August'),
    ('9', 'September'),
    ('10', 'October'),
    ('11', 'November'),
    ('12', 'December')
)

PALETTES = (
    ('EU', 'Euro'),
    ('OR', 'Ordinary')
)

PALETTES_STATUS = (
    ('DEL', 'Delivered'),
    ('RET', 'returned')
)

ITEM_SORTS = (
    ('201', 'FEFCO 201'),
    ('202', 'FEFCO 202'),
    ('203', 'FEFCO 203'),
    ('301', 'FEFCO 301'),
    ('409', 'FEFCO 409'),
    ('SZTANCA', 'Sztanca'),
    ('PRZEKLADKA', 'Przekładka'),
    ('MAG', 'Magazyn'),
    ('ROT/TYG', 'Rotacja/Tygiel')
)

CARDBOARD_TYPES = (
    ('3B', '3B'),
    ('3C', '3C'),
    ('3E', '3E'),
    ('5BC', '5BC'),
    ('5EB', '5EB'),
    ('BB', 'BB'),
    ('BCS', 'BCS'),
    ('BS', 'BS')
)

CARDBOARD_SORT = (
    ('B', 'B'),
    ('C', 'C'),
    ('E', 'E'),
    ('BC', 'BC'),
    ('EB', 'EB')
)

GENRES = (
    ('Ordinary', 'Ordinary'),
    ('To Do List', 'To Do List'),
    ('Journal', 'Journal'),
    ('Notice', 'Notice')
)

ABSENCE_TYPES = (
    ('NN', 'Nieobecność nieusprawiedliwiona'),
    ('UW', 'Urlop wypoczynkowy'),
    ('UŻ', 'Urlop na żądanie'),
    ('UO', 'Urlop okolicznościowy'),
    ('SP', 'Spóźnienie'),
    ('UB', 'Urlop bezpłatny'),
    ('CH', 'Chorobowe'),
    ('KW', 'Kwarantanna'),
    ('OP', 'Opieka nad członkiem rodziny'),
    ('D', 'Delegacja'),
    ('IN', 'Inne'),
    ('IZ', 'Izolacja'),
    ('PO', 'Postojowe')
)

PUNCH_TYPES = (
    ('471', 'FEFCO 471'),
    ('427', 'FEFCO 427'),
    ('426', 'FEFCO 426'),
    ('421', 'FEFCO 421'),
    ('201', 'FEFCO 201'),
    ('SWT', 'Spody, wieka, tacki'),
    ('KR', 'Krata'),
    ('NR', 'Narożnik'),
    ('PDK', 'Pozostałe do klejenia'),
    ('WK', 'Wkład'),
    ('INNE', 'Inne')
)

PRODUCTION_TYPES = (
    ('KLSD', 'KLEJENIE-SKLEJARKA-DUŻA'),
    ('KLSM', 'KLEJENIE-SKLEJARKA-MAŁA'),
    ('KLR', 'KLEJENIE-RĘCZNE'),
    ('DR', 'DRUKOWANIE'),
    ('WY', 'WYCINANIE'),
    ('WY+DR', 'WYCINANIE Z NADRUKIEM'),
    ('SZ', 'SZTANCOWANIE'),
    ('OB', 'OBRYWANIE'),
    ('PK', 'PAKOWANIE'),
    ('INNE', 'INNE')
)

POLYMERS_PRODUCERS = (
    ('AMBR', 'AMBR'),
    ('CHESPA', 'CHESPA')
)

CONTRACT_TYPES = (
    ('UOP', 'Umowa o pracę'),
    ('UZ', 'Umowa zlecenie'),
    ('FZ', 'Firma zewnętrzna')
)

OCCUPANCY_TYPE = (
    ('MECHANIC', 'MECHANIC'),
    ('PRODUCTION', 'PRODUCTION'),
    ('OFFICE', 'OFFICE'),
    ('OTHER', 'OTHER'),
    ('MANAGEMENT', 'MANAGEMENT'),
    ('LOGISTIC', 'LOGISTIC')
)


class Person(models.Model):
    first_name = models.CharField(max_length=32)
    last_name = models.CharField(max_length=32)
    email_address = models.EmailField()
    telephone = models.CharField(max_length=16)
    job_start = models.DateField(default=datetime.datetime.strptime('01-01-2017', '%d-%m-%Y'))
    job_end = models.DateField(blank=True, null=True)
    occupancy_type = models.CharField(max_length=32, default='PRODUCTION', choices=OCCUPANCY_TYPE)
    medical_examination = models.DateField(blank=True, null=True)
    yearly_vacation_limit = models.PositiveIntegerField(default=0)
    amount_2020 = models.IntegerField(null=True, blank=True, default=0)
    user = models.OneToOneField(User, on_delete=models.PROTECT, null=True, blank=True)

    class Meta:
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return '{} {}'.format(self.first_name, self.last_name)

    def get_initials(self):
        return '{}{}'.format(self.first_name[0:2], self.last_name[0:2])

    # def vacation_days(self, year):
    #     r = 0
    #     if year == '2021':
    #         r += self.amount_2021 + self.yearly_vacation_limit
    #     else:
    #         r += self.yearly_vacation_limit + self.vacation_days(str(int(year) - 1))
    #     for a in Absence.objects.filter(worker=self, absence_date__gt=datetime.date(2020, 12, 31)):
    #         if a.absence_type == 'UW':
    #             r -= 1
    #     return r
    #
    # def vacation_last_from_year(self, year):
    #     r = 0
    #     if year == '2020':
    #         r = self.amount_2021
    #     else:
    #         r = self.vacation_days(str(year)) - self.amount_2021
    #
    #     return r

    def end_year_vacation(self, year):
        if year < 2020:
            return 0
        elif year == 2020:
            return self.amount_2020
        else:
            if year == 2021:
                r = self.amount_2020 + self.yearly_vacation_limit
                for a in Absence.objects.filter(worker=self, absence_date__gt=datetime.date(2020, 12, 31),
                                                absence_date__lte=datetime.date(2021, 12, 31)):
                    if a.absence_type == 'UW':
                        r -= 1
                return r
            else:
                return self.end_year_vacation(year - 1) + self.yearly_vacation_limit

    def available_vacation_days(self):
        contracts = Contract.objects.filter(worker=self, type='UOP').order_by('date_start')
        days = 0
        if contracts:
            start_day = contracts[0].date_start
            start_year = contracts[0].date_start.year
            while start_year != datetime.datetime.today().year:
                days += 26
                start_year += 1
        return days

    def all_vacation_days(self):
        contracts = Contract.objects.filter(worker=self, type='UOP').order_by('date_start')
        days = 0
        if contracts:
            first_contract_start = contracts[0].date_start
            last_contract_end = list(contracts)[-1].date_end
            base_value = 26
            for year in range(first_contract_start.year, datetime.date.today().year + 1):
                year_days = 366 if year % 4 == 0 and year % 100 != 0 else 365
                days_until_start = 0
                days_till_end = 0
                if year == first_contract_start.year:
                    days_until_start = (first_contract_start - datetime.date(year, 1, 1)).days
                if last_contract_end:
                    if year == last_contract_end.year:
                        days_till_end = (datetime.date(year, 12, 31) - last_contract_end).days

                days += base_value * ((year_days - days_till_end - days_until_start)/year_days)
                days = int(round(days, 0))

                print(self, year, days, days_till_end, days_until_start)
        return days

    def used_vacation_during_year(self, year):
        start = datetime.date(year, 1, 1)
        end = datetime.date(year, 12, 31)
        used_vacation = Absence.objects.filter(worker=self, absence_date__gte=start, absence_date__lte=end,
                                               absence_type__in=['UW', 'UŻ'])
        return len(used_vacation)

    def vacation_from_last_year(self):
        pass

    def status(self):
        if self.job_end:
            return 'not active'
        return 'active'

    def days_at_work(self, year=None, start=None, end=None):

        year_start = datetime.datetime.strptime('01-01-{}'.format(year), '%d-%m-%Y')
        year_end = datetime.datetime.strptime('31-12-{}'.format(year), '%d-%m-%Y')
        if not start:
            start = year_start
            if self.job_start:
                if self.job_start.year == start.year:
                    start = self.job_start
                elif self.job_start > start.date():
                    start = year_end + datetime.timedelta(days=1)
        if not end:
            end = year_end
            if int(year) == datetime.date.today().year:
                end = datetime.datetime.today()
            if self.job_end:
                if self.job_end.year == end.year:
                    end = self.job_end

        if isinstance(start, datetime.datetime):
            start = start.date()
        if isinstance(end, datetime.datetime):
            end = end.date()

        holidays = Holiday.objects.filter(holiday_date__gte=start, holiday_date__lte=end)
        workdays = work_days_during_period(year=year, start=start, end=end)

        absences = Absence.objects.filter(worker=self, absence_date__gte=start, absence_date__lte=end,
                                          absence_type__in=['UW', 'UB', 'CH', 'OP', 'NN', 'KW', 'UO'])

        new_holidays = [h for h in holidays if h.holiday_date.weekday() < 5]

        holidays = new_holidays

        return workdays - len(holidays) - len(absences)

    def absences_types(self, year=None, start=None, end=None):
        year_start = datetime.datetime.strptime('01-01-{}'.format(year), '%d-%m-%Y')
        year_end = datetime.datetime.strptime('31-12-{}'.format(year), '%d-%m-%Y')
        if not start:
            start = year_start
            if self.job_start:
                if self.job_start.year == start.year:
                    start = self.job_start
                elif self.job_start > start.date():
                    start = year_end + datetime.timedelta(days=1)
        if not end:
            end = year_end
            if int(year) == datetime.date.today().year:
                end = datetime.datetime.today()
            if self.job_end:
                if self.job_end.year == end.year:
                    end = self.job_end

        if isinstance(start, datetime.datetime):
            start = start.date()
        if isinstance(end, datetime.datetime):
            end = end.date()

        absences = Absence.objects.filter(absence_date__gte=start, absence_date__lte=end, worker=self)

        result = []

        not_counted_types = ('D', 'SP')

        for x, y in ABSENCE_TYPES:
            if x not in not_counted_types:
                absences_to_add = absences.filter(absence_type=x)
                if len(absences_to_add) > 0:
                    result.append((x, len(absences_to_add)))

        return result

    @classmethod
    def active_workers_at_day(cls, day):
        active_workers = []
        workers = cls.objects.filter(job_start__lte=day)
        for worker in workers:
            if worker.job_end:
                if day <= worker.job_end:
                    active_workers.append(worker)
            else:
                active_workers.append(worker)

        print(active_workers)

        return active_workers

    @classmethod
    def active_workers_at_month(cls, year, month):
        if month == 2:
            if year % 4 == 0:
                days = 29
            else:
                days = 28
        elif month in (1, 3, 5, 7, 8, 10, 12):
            days = 31
        else:
            days = 30

        month_start = datetime.datetime.strptime(f'{year}-{month}-01', '%Y-%m-%d').date()
        month_end = datetime.datetime.strptime(f'{year}-{month}-{days}', '%Y-%m-%d').date()

        active_workers = []
        workers = cls.objects.filter(job_start__lte=month_end)
        for worker in workers:
            if worker.job_end:
                if month_start <= worker.job_end:
                    active_workers.append(worker)
            else:
                active_workers.append(worker)

        return active_workers

    @classmethod
    def workers_at_work(cls, day):
        day_workers = []
        active_workers = []
        workers = cls.objects.filter(job_start__lte=day)
        for worker in workers:
            if worker.job_end:
                if day <= worker.job_end:
                    active_workers.append(worker)
            else:
                active_workers.append(worker)
        for worker_ in active_workers:
            absence = Absence.objects.filter(worker=worker_, absence_date=day)
            if absence.count() == 0:
                day_workers.append(worker_)

        return day_workers

    @classmethod
    def active_hours_per_day(cls, day):
        workers = cls.workers_at_work(day)
        data = [0 for _ in range(6)]
        for w in workers:
            hours = 8
            extra_hours = ExtraHour.objects.filter(worker=w, extras_date=day)
            if extra_hours:
                hours = 8 + extra_hours[0].quantity if extra_hours[0].full_day else extra_hours[0].quantity
            if w.occupancy_type == 'PRODUCTION':
                data[0] += hours
            elif w.occupancy_type == 'OFFICE':
                data[1] += hours
            elif w.occupancy_type == 'MANAGEMENT':
                data[2] += hours
            elif w.occupancy_type == 'LOGISTIC':
                data[3] += hours
            elif w.occupancy_type == 'MECHANIC':
                data[4] += hours
            else:
                data[5] += hours
        return data


class CardboardProvider(models.Model):
    name = models.CharField(max_length=32)
    shortcut = models.CharField(max_length=6, blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name}'


class Buyer(models.Model):
    name = models.CharField(max_length=32)
    shortcut = models.CharField(max_length=32)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Order(models.Model):
    provider = models.ForeignKey(CardboardProvider, on_delete=models.CASCADE)
    order_provider_number = models.IntegerField()
    date_of_order = models.DateField()
    is_completed = models.BooleanField(default=False)

    class Meta:
        ordering = ['date_of_order', 'order_provider_number']

    def __str__(self):
        return '{} {}'.format(self.provider, self.order_provider_number)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    item_number = models.IntegerField()
    sort = models.CharField(max_length=15, choices=ITEM_SORTS)
    dimension_one = models.IntegerField()
    dimension_two = models.IntegerField()
    dimension_three = models.IntegerField(blank=True, null=True)
    scores = models.CharField(max_length=64)
    format_width = models.IntegerField()
    format_height = models.IntegerField()
    ordered_quantity = models.IntegerField()
    buyer = models.ManyToManyField(Buyer, blank=True)
    cardboard_type = models.CharField(max_length=8, choices=CARDBOARD_TYPES)
    cardboard_weight = models.IntegerField()
    cardboard_additional_info = models.CharField(max_length=32, default='', blank=True)
    name = models.CharField(max_length=16, blank=True)
    is_completed = models.BooleanField(default=False)
    planned_delivery = models.DateField(blank=True, null=True)

    class Meta:
        ordering = ['order__date_of_order', 'order__provider__name', 'order__order_provider_number', 'item_number']

    def __str__(self):
        return '{}/{}: {}x{}'.format(self.order, self.item_number, self.format_width, self.format_height)


class Palette(models.Model):
    width = models.PositiveIntegerField(default=1200)
    height = models.PositiveIntegerField(default=800)
    type = models.CharField(max_length=4, choices=PALETTES)

    def __str__(self):
        return f'{self.type} {self.width}x{self.height}'


class Delivery(models.Model):
    items = models.ManyToManyField(OrderItem, through='OrderItemQuantity')
    provider = models.ForeignKey(CardboardProvider, on_delete=models.CASCADE)
    date_of_delivery = models.DateField()
    palettes = models.ManyToManyField(Palette, through='PaletteQuantity')

    class Meta:
        ordering = ['date_of_delivery']

    def __str__(self):
        return f'{self.provider}|{self.date_of_delivery}'

    @classmethod
    def deliveries_during_period(cls, year):
        result = []
        year_start = datetime.datetime.strptime('01-01-{}'.format(year), '%d-%m-%Y')
        year_end = datetime.datetime.strptime('31-12-{}'.format(year), '%d-%m-%Y')
        year_deliveries = cls.objects.filter(date_of_delivery__gte=year_start, date_of_delivery__lte=year_end)

        for d in year_deliveries:
            result.append((1, d.date_of_delivery.month))

        chart_data = []

        for m in MONTHS:
            chart_data.append([m[0], m[1], 0])

        for d in result:
            chart_data[d[1] - 1][2] += 1

        chart_data = list(filter(lambda x: x[2] > 0, chart_data))

        return chart_data


class OrderItemQuantity(models.Model):
    delivery = models.ForeignKey(Delivery, on_delete=models.CASCADE)
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=0)
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.order_item.order}/{self.order_item.item_number} - {self.order_item.format_width} x {self.order_item.format_height}'


class PaletteQuantity(models.Model):
    delivery = models.ForeignKey(Delivery, on_delete=models.CASCADE)
    palette = models.ForeignKey(Palette, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=0)
    status = models.CharField(max_length=4, choices=PALETTES_STATUS, default='DEL')

    @classmethod
    def all_quantities_between_dates(cls, provider=None, palette_type=None, palette_dimensions=None, status=None,
                                     date_from=None,
                                     date_to=None):

        provider = 'AQ' if not provider else provider
        palette_type = 'EU' if not palette_type else palette_type
        palette_dimensions = '1200x800' if not palette_dimensions else palette_dimensions
        status = 'DEL' if not status else status

        result = 0
        provider_object = CardboardProvider.objects.get(shortcut=provider)
        width, height = palette_dimensions.split('x')
        palette_object = Palette.objects.get(type=palette_type, width=int(width), height=int(height))

        if not date_from:
            date_from = datetime.datetime.strptime('2017-01-01', '%Y-%m-%d')
        else:
            date_from = datetime.datetime.strptime(date_from, '%Y-%m-%d')

        if not date_to:
            date_to = datetime.date.today()
        else:
            date_to = datetime.datetime.strptime(date_to, '%Y-%m-%d')

        all_deliveries = Delivery.objects.filter(provider=provider_object, date_of_delivery__gte=date_from,
                                                 date_of_delivery__lte=date_to)

        for d in all_deliveries:
            q = cls.objects.filter(delivery=d, palette=palette_object, status=status)
            if q:
                for x in q:
                    result += x.quantity

        return result


class Machine(models.Model):
    name = models.CharField(max_length=32)
    shortcut = models.CharField(max_length=16)

    def __str__(self):
        return self.shortcut


class Note(models.Model):
    add_date = models.DateTimeField(auto_now_add=True)
    genre = models.CharField(max_length=16, choices=GENRES, default='Ordinary')
    title = models.CharField(max_length=32, default='Note')
    content = models.TextField()


class Absence(models.Model):
    worker = models.ForeignKey(Person, on_delete=models.CASCADE)
    absence_date = models.DateField()
    absence_type = models.CharField(max_length=4, choices=ABSENCE_TYPES)
    value = models.IntegerField(null=True, blank=True)
    additional_info = models.CharField(max_length=255, null=True, blank=True)

    # create acquaintance with value in minutes
    def create_acquaintance(self, value):
        if isinstance(value, int):
            if self.absence_type == 'SP':
                self.value = value
                self.save()
            else:
                pass
        else:
            return TypeError('Acquaintance value must be a float')

    # create unusual absence type
    def create_unusual(self, additional_info):
        if self.absence_type == 'IN':
            self.additional_info = additional_info
            self.save()
        else:
            pass

    def __str__(self):
        return f'{self.absence_date} {self.worker}({self.absence_type})'


class Holiday(models.Model):
    name = models.CharField(max_length=32)
    holiday_date = models.DateField(unique=True)

    def __str__(self):
        return f'{self.name}({self.holiday_date})'

    class Meta:
        ordering = ['-holiday_date']


class ExtraHour(models.Model):
    worker = models.ForeignKey(Person, on_delete=models.CASCADE)
    extras_date = models.DateField()
    quantity = models.DecimalField(max_digits=3, decimal_places=1)
    full_day = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.worker} {self.extras_date} {self.quantity}'


class Punch(models.Model):
    type = models.CharField(max_length=8, choices=PUNCH_TYPES)
    type_letter = models.CharField(max_length=4, default='', blank=True)
    type_num = models.DecimalField(max_digits=4, decimal_places=1)
    name = models.CharField(max_length=96, default='', blank=True)
    dimension_one = models.IntegerField(blank=True, null=True)
    dimension_two = models.IntegerField(blank=True, null=True)
    dimension_three = models.IntegerField(blank=True, null=True)
    quantity = models.IntegerField(default=1)
    size_one = models.IntegerField()
    size_two = models.IntegerField()
    cardboard = models.CharField(max_length=4, choices=CARDBOARD_SORT)
    pressure_large = models.IntegerField(default=0)
    pressure_small = models.IntegerField(default=0)
    wave_direction = models.BooleanField(default=True)
    customers = models.ManyToManyField(Buyer, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['type', 'type_letter', 'type_num']

    def __str__(self):
        sign = f'{self.type}'
        if self.type_letter:
            sign += f' {self.type_letter}'
        sign += str(self.type_num) if self.type_num % 1 != 0 else str(int(self.type_num))
        if self.dimension_one and self.dimension_two:
            if self.dimension_three:
                return f'{sign}: {self.dimension_one}x{self.dimension_two}x{self.dimension_three}'
            else:
                return f'{sign}: {self.dimension_one}x{self.dimension_two}'
        else:
            return f'{sign}: {self.size_one}x{self.size_two}'

    def punch_name(self):
        z = float(self.type_num)
        if ((z * 10) % 10) != 0.0:
            return f'{self.type}||{self.type_letter}{z}'
        return f'{self.type}||{self.type_letter}{int(z)}'

    def punch_usage(self):
        from production.models import ProductionUnit
        units = ProductionUnit.objects.filter(punch=self, status="FINISHED")
        return units


class PunchProduction(models.Model):
    punch = models.ForeignKey(Punch, on_delete=models.PROTECT)
    worker = models.ForeignKey(Person, on_delete=models.PROTECT, blank=True, null=True)
    cardboard = models.ManyToManyField(OrderItemQuantity, blank=True)
    date_start = models.DateField()
    date_end = models.DateField()
    quantity = models.IntegerField()
    comments = models.CharField(max_length=128, blank=True)

    def __str__(self):
        return f'{self.punch}/{self.date_end}/{self.quantity}'

    class Meta:
        ordering = ['date_end']


class SpreadsheetCopy(models.Model):
    gs_id = models.CharField(max_length=48)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.created)


class DailyReport(models.Model):
    date = models.DateField()
    add_date = models.DateField(auto_created=True)
    last_modification = models.DateField(auto_now=True)
    workers = models.ManyToManyField(Person)
    description = models.TextField()


class Color(models.Model):
    name = models.CharField(max_length=32, blank=True, null=True)
    number = models.CharField(max_length=12, blank=True, null=True)
    availability = models.DecimalField(default=0, max_digits=4, decimal_places=1)
    red = models.PositiveIntegerField(blank=True, null=True)
    green = models.PositiveIntegerField(blank=True, null=True)
    blue = models.PositiveIntegerField(blank=True, null=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.number}({self.name})'

    def color_status(self):
        result = self.availability
        delivery = ColorDelivery.objects.filter(color=self)
        usage = ColorUsage.objects.filter(color=self)
        for d in delivery:
            result += d.weight
        for u in usage:
            result -= u.value
        return result


class ColorSpecialEvent(models.Model):
    color = models.ForeignKey(Color, on_delete=models.CASCADE)
    event = models.CharField(max_length=32)
    date = models.DateField()
    difference = models.DecimalField(max_digits=4, decimal_places=1)
    description = models.CharField(max_length=255, null=True, blank=True)


class ColorDelivery(models.Model):
    color = models.ForeignKey(Color, on_delete=models.CASCADE)
    company = models.CharField(max_length=20, blank=True, null=True)
    weight = models.PositiveIntegerField()
    date = models.DateField(blank=True, null=True)

    def __str__(self):
        return f'{self.company} - {self.color} - {self.weight}'


class Photopolymer(models.Model):
    producer = models.CharField(max_length=16, choices=POLYMERS_PRODUCERS)
    project = models.FileField(upload_to='projects', null=True, blank=True)
    colors = models.ManyToManyField(Color)
    identification_number = models.IntegerField()
    identification_letter = models.CharField(max_length=8, blank=True, null=True)
    customer = models.ForeignKey(Buyer, on_delete=models.PROTECT)
    dimensions = models.CharField(max_length=32, blank=True, null=True)
    name = models.CharField(max_length=128, default='')
    delivery_date = models.DateField(blank=True, null=True,
                                     default=datetime.datetime.strptime('2017-01-01', '%Y-%M-%d'))
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['identification_number']

    def __str__(self):
        if self.identification_letter:
            result = f'{self.identification_number}{self.identification_letter}/{self.customer}'
        else:
            result = f'{self.identification_number}/{self.customer}'
        if self.name != '':
            result += f' {self.name}'
        return result

    def polymer_usage(self):
        from production.models import ProductionUnit
        units = ProductionUnit.objects.filter(polymer=self, status="FINISHED")
        return units

    def presence(self):
        if not self.delivery_date or self.delivery_date >= datetime.date.today():
            return False
        else:
            services = PhotopolymerService.objects.filter(photopolymer=self)

            if len(services) == 0:
                return True
            else:
                result = True
                for s in services:
                    if s.status():
                        result = None
                return result

    def get_absolute_url(self):
        return reverse('polymer-details', kwargs={'polymer_id': self.pk})


class PhotopolymerService(models.Model):
    photopolymer = models.ForeignKey(Photopolymer, on_delete=models.CASCADE)
    send_date = models.DateField()
    company = models.CharField(max_length=16, default='')
    service_description = models.CharField(max_length=200)
    return_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return f'{self.photopolymer.identification_number}|{self.photopolymer.producer} {self.photopolymer.customer}'

    def status(self):
        if not self.return_date:
            return True
        else:
            if self.return_date < datetime.date.today():
                return False
            else:
                return True

    def get_absolute_url(self):
        return reverse('service-details', kwargs={'pk': self.pk})


class UserVisitCounter(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    page = models.CharField(max_length=64)
    counter = models.PositiveIntegerField(default=0)
    first_visit = models.DateTimeField(null=True, blank=True)
    last_visit = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'{self.user}/{self.page}: {self.counter}'

    class Meta:
        ordering = ['-last_visit']


class ProductionProcess(models.Model):
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE)
    production = models.ForeignKey('self', blank=True, null=True, on_delete=models.CASCADE)
    stock = models.ManyToManyField(OrderItemQuantity, blank=True)
    type = models.CharField(max_length=8, choices=PRODUCTION_TYPES)
    worker = models.ManyToManyField(Person, blank=True)
    machine = models.ForeignKey(Machine, blank=True, null=True, on_delete=models.PROTECT)
    quantity_start = models.IntegerField(default=0)
    quantity_end = models.IntegerField(default=0)
    date_start = models.DateField(blank=True, null=True)
    date_end = models.DateField(blank=True, null=True)
    punch = models.ForeignKey(Punch, blank=True, null=True, on_delete=models.PROTECT)
    polymer = models.ForeignKey(Photopolymer, blank=True, null=True, on_delete=models.PROTECT)
    note = models.CharField(max_length=300, null=True, blank=True)

    def __str__(self):
        order_name = '{}){}/{} | {} - {}'.format(self.date_end, self.order_item.order, self.order_item.item_number,
                                                 self.type, self.quantity_end)

        return order_name


class ColorUsage(models.Model):
    production = models.ForeignKey(ProductionProcess, blank=True, null=True, on_delete=models.CASCADE)
    color = models.ForeignKey(Color, on_delete=models.CASCADE)
    value = models.DecimalField(max_digits=3, decimal_places=1)


class Contract(models.Model):
    worker = models.ForeignKey(Person, on_delete=models.CASCADE)
    type = models.CharField(choices=CONTRACT_TYPES, max_length=8)
    position = models.CharField(max_length=64)
    date_start = models.DateField()
    date_end = models.DateField(null=True, blank=True)
    salary = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    extra_info = models.CharField(max_length=255, null=True, blank=True)
    first = models.BooleanField(default=False)

    class Meta:
        ordering = ['worker', 'date_end']

    def get_absolute_url(self):
        return reverse('person-details', kwargs={'person_id': self.worker.id})

    def __str__(self):
        if self.date_end:
            return f'{self.worker} - {self.position} ({self.date_start} - {self.date_end})'
        else:
            return f'{self.worker} - {self.position} ({self.date_start} - ∞)'

    @classmethod
    def contracts_during_the_month(cls, month=None, year=None, contract_type=None):
        from calendar import monthrange
        if not month:
            month = datetime.datetime.today().month
        if not year:
            year = datetime.datetime.today().year
        contracts = cls.objects.filter(date_start__lte=datetime.date(year, month, monthrange(year, month)[1]))
        temp_contracts = []
        for contract in contracts:
            if not contract.date_end:
                if not contract_type:
                    temp_contracts.append(contract)
                elif contract.type == contract_type:
                    temp_contracts.append(contract)
            else:
                if contract.date_end >= datetime.date(year, month, 1):
                    if not contract_type:
                        temp_contracts.append(contract)
                    elif contract.type == contract_type:
                        temp_contracts.append(contract)

        return temp_contracts


class Reminder(models.Model):
    worker = models.ForeignKey(Person, on_delete=models.CASCADE)
    title = models.CharField(max_length=64)
    create_date = models.DateField()
    sent_date = models.DateField(blank=True, null=True)

    def __str__(self):
        if self.sent_date:
            return f'SEND / {self.worker} - {self.title}'
        else:
            return f'-- / {self.worker} - {self.title}'


class PaletteCustomer(models.Model):
    customer = models.ForeignKey(Buyer, on_delete=models.CASCADE)
    palette = models.ForeignKey(Palette, on_delete=models.PROTECT)
    quantity = models.IntegerField(default=0)
    status = models.CharField(max_length=4, choices=PALETTES_STATUS, default='DEL')
    date = models.DateField()
    exchange = models.BooleanField(default=False)
    extra_info = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f'{self.customer} - {self.palette} ({self.status} - {self.quantity}) - {self.date}'

    @classmethod
    def customer_palette_number(cls, customer, palette):
        result = 0
        for c in cls.objects.filter(customer=customer, palette=palette):
            if c.status == 'DEL':
                if not c.exchange:
                    result += c.quantity
            else:
                if not c.exchange:
                    result -= c.quantity

        return result


class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_sender')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_recipient')
    title = models.CharField(max_length=64)
    content = models.TextField()
    date_sent = models.DateTimeField(blank=True, null=True)
    date_read = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f'{self.sender} -> {self.recipient} ({self.date_sent})'


class Cloth(models.Model):
    name = models.CharField(max_length=64)
    description = models.CharField(max_length=512, null=True, blank=True)

    def __str__(self):
        return self.name


class WorkerWorkWear(models.Model):
    worker = models.ForeignKey(Person, on_delete=models.CASCADE)
    cloth = models.ForeignKey(Cloth, on_delete=models.CASCADE)
    number_or_size = models.CharField(max_length=16, null=True, blank=True)
    date = models.DateField()

    def __str__(self):
        return str(self.date) + ' ' + str(self.worker) + ' ' + str(self.cloth)

    class Meta:
        ordering = ['-date']


class WorkReminder(models.Model):
    title = models.CharField(max_length=64, default='Reminder')
    add_date = models.DateTimeField(auto_now_add=True)
    content = models.TextField(null=True, blank=True)
    active = models.BooleanField(default=True)
    alert_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'{self.title} - {self.add_date}'


class GluerNumber(models.Model):
    number = models.PositiveIntegerField()
    customer = models.ForeignKey(Buyer, on_delete=models.PROTECT)
    dimensions = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=32)
    comments = models.CharField(max_length=128, null=True, blank=True)

    def __str__(self):
        return f'[{self.number}] {self.customer} - {self.dimensions}'
