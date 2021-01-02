from django.db import models
from django.db.models.functions import ExtractYear
import decimal
import datetime

ITEM_SORTS = (
    ('201', 'FEFCO 201'),
    ('202', 'FEFCO 202'),
    ('203', 'FEFCO 203'),
    ('301', 'FEFCO 301'),
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
    ('UZ', 'Urlop zdrowotny')
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


class Person(models.Model):
    first_name = models.CharField(max_length=32)
    last_name = models.CharField(max_length=32)
    email_address = models.EmailField()
    telephone = models.CharField(max_length=16)
    job_start = models.DateField(default=datetime.datetime.strptime('01-01-2017', '%d-%m-%Y'))
    job_end = models.DateField(blank=True, null=True)

    class Meta:
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return '{} {}'.format(self.first_name, self.last_name)

    def get_initials(self):
        return '{}{}'.format(self.first_name[0:2], self.last_name[0:2])


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

    class Meta:
        ordering = ['order__provider__name', 'order__order_provider_number', 'item_number']

    def __str__(self):
        return '{}/{}: {}x{}'.format(self.order, self.item_number, self.format_width, self.format_height)


class Delivery(models.Model):
    items = models.ManyToManyField(OrderItem, through='OrderItemQuantity')
    provider = models.ForeignKey(CardboardProvider, on_delete=models.CASCADE)
    date_of_delivery = models.DateField()

    class Meta:
        ordering = ['date_of_delivery']

    def __str__(self):
        return f'{self.provider}|{self.date_of_delivery}'


class OrderItemQuantity(models.Model):
    delivery = models.ForeignKey(Delivery, on_delete=models.CASCADE)
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.order_item.order}/{self.order_item.item_number} - {self.order_item.format_width} x {self.order_item.format_height}'


class Machine(models.Model):
    name = models.CharField(max_length=32)
    shortcut = models.CharField(max_length=16)


class Note(models.Model):
    add_date = models.DateTimeField(auto_now_add=True)
    genre = models.CharField(max_length=16, choices=GENRES, default='Ordinary')
    title = models.CharField(max_length=32, default='Note')
    content = models.TextField()


class Absence(models.Model):
    worker = models.ForeignKey(Person, on_delete=models.CASCADE)
    absence_date = models.DateField()
    absence_type = models.CharField(max_length=4, choices=ABSENCE_TYPES)

    def __str__(self):
        return f'{self.absence_date} {self.worker}'


class Holiday(models.Model):
    name = models.CharField(max_length=32)
    holiday_date = models.DateField(unique=True)


class ExtraHour(models.Model):
    worker = models.ForeignKey(Person, on_delete=models.CASCADE)
    extras_date = models.DateField()
    quantity = models.DecimalField(max_digits=3, decimal_places=1)

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
    cardboard = models.CharField(max_length=4, choices=CARDBOARD_TYPES)
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


class ProductionProcess(models.Model):
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE)
    production = models.ForeignKey('self', blank=True, null=True, on_delete=models.CASCADE)
    stock = models.ManyToManyField(OrderItemQuantity)
    type = models.CharField(max_length=8, choices=PRODUCTION_TYPES)
    worker = models.ManyToManyField(Person, blank=True)
    machine = models.ForeignKey(Machine, blank=True, null=True, on_delete=models.PROTECT)
    quantity_start = models.IntegerField()
    quantity_end = models.IntegerField()
    date_start = models.DateField()
    date_end = models.DateField()
    punch = models.ForeignKey(Punch, blank=True, null=True, on_delete=models.PROTECT)

    def __str__(self):
        order_name = '{}/{} | {}'.format(self.order_item.order, self.order_item.item_number, self.type)

        return order_name


class SpreadsheetCopy(models.Model):
    gs_id = models.CharField(max_length=48)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.created)
