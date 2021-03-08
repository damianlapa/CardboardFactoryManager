from django.db import models
from django.db.models.functions import ExtractYear
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import User
from django.urls import reverse
import decimal
import datetime

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
    ('UO', 'Urlop okolicznościowy'),
    ('SP', 'Spóźnienie'),
    ('UB', 'Urlop bezpłatny'),
    ('CH', 'Chorobowe'),
    ('KW', 'Kwarantanna')
)

PUNCH_TYPES = (
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
    ('UZ', 'Umowa zlecenie')
)


class Person(models.Model):
    first_name = models.CharField(max_length=32)
    last_name = models.CharField(max_length=32)
    email_address = models.EmailField()
    telephone = models.CharField(max_length=16)
    job_start = models.DateField(default=datetime.datetime.strptime('01-01-2017', '%d-%m-%Y'))
    job_end = models.DateField(blank=True, null=True)
    medical_examination = models.DateField(blank=True, null=True)
    yearly_vacation_limit = models.PositiveIntegerField(default=0)
    amount_2020 = models.IntegerField(null=True, blank=True, default=0)

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

    def __str__(self):
        return f'{self.absence_date} {self.worker}({self.absence_type})'


class Holiday(models.Model):
    name = models.CharField(max_length=32)
    holiday_date = models.DateField(unique=True)


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
    name = models.CharField(max_length=24, default='', blank=True)
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

    def __str__(self):
        if self.dimension_one and self.dimension_two:
            if self.dimension_three:
                return f'{self.type}: {self.dimension_one}x{self.dimension_two}x{self.dimension_three}'
            else:
                return f'{self.type}: {self.dimension_one}x{self.dimension_two}'
        else:
            return f'{self.type}: {self.size_one}x{self.size_two}'

    def punch_name(self):
        z = float(self.type_num)
        if ((z * 10) % 10) != 0.0:
            return f'{self.type}||{self.type_letter}{z}'
        return f'{self.type}||{self.type_letter}{int(z)}'


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
    customer = models.ForeignKey(Buyer, on_delete=models.PROTECT)
    name = models.CharField(max_length=32, default='')
    delivery_date = models.DateField(blank=True, null=True,
                                     default=datetime.datetime.strptime('2017-01-01', '%Y-%M-%d'))

    class Meta:
        ordering = ['-delivery_date']

    def __str__(self):
        result = f'{self.identification_number}/{self.customer}'
        if self.name != '':
            result += f' {self.name}'
        return result

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
    page = models.CharField(max_length=32)
    counter = models.PositiveIntegerField(default=0)
    first_visit = models.DateTimeField(null=True, blank=True)
    last_visit = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'{self.user}/{self.page}: {self.counter}'


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

    def get_absolute_url(self):
        return reverse('person-details', kwargs={'person_id': self.worker.id})

    def __str__(self):
        if self.date_end:
            return f'{self.worker} - {self.position} ({self.date_start} - {self.date_end})'
        else:
            return f'{self.worker} - {self.position} ({self.date_start} - ∞)'


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
