from django.db import models
from django.db.models.functions import ExtractYear
import datetime


ITEM_SORTS = (
    ('201', 'FEFCO 201'),
    ('202', 'FEFCO 202'),
    ('203', 'FEFCO 203'),
    ('SZTANCA', 'Sztanca'),
    ('PRZEKLADKA', 'Przekładka')
)

CARDBOARD_TYPES = (
    ('B', 'B'),
    ('C', 'C'),
    ('E', 'E'),
    ('BC', 'BC'),
    ('BE', 'BE')
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


class Person(models.Model):
    first_name = models.CharField(max_length=32)
    last_name = models.CharField(max_length=32)
    email_address = models.EmailField()
    telephone = models.CharField(max_length=16)

    def __str__(self):
        return '{} {}'.format(self.first_name, self.last_name)


class CardboardProvider(models.Model):
    name = models.CharField(max_length=32)
    employers = models.ManyToManyField(Person, blank=True)

    def __str__(self):
        return self.name


class Buyer(models.Model):
    name = models.CharField(max_length=32)
    employers = models.ManyToManyField(Person, blank=True)

    def __str__(self):
        return self.name


class Order(models.Model):
    provider = models.ForeignKey(CardboardProvider, on_delete=models.CASCADE)
    order_provider_number = models.IntegerField()
    date_of_order = models.DateTimeField()
    is_completed = models.BooleanField(default=False)

    def __str__(self):
        return '{} {}'.format(self.provider, self.order_provider_number)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    item_number = models.IntegerField()
    sort = models.CharField(max_length=15, choices=ITEM_SORTS)
    format_width = models.IntegerField()
    format_height = models.IntegerField()
    ordered_quantity = models.IntegerField()
    buyer = models.ManyToManyField(Buyer, blank=True)
    cardboard_type = models.CharField(max_length=8, choices=CARDBOARD_TYPES)
    cardboard_weight = models.IntegerField()
    dimension_one = models.IntegerField()
    dimension_two = models.IntegerField()
    dimension_three = models.IntegerField(blank=True, null=True)
    scores = models.CharField(max_length=64)

    class Meta:

        ordering = ['item_number']

    def __str__(self):
        return '{}/{}'.format(self.order, self.item_number)


class Delivery(models.Model):
    items = models.ManyToManyField(OrderItem, through='OrderItemQuantity')
    provider = models.ForeignKey(CardboardProvider, on_delete=models.CASCADE)
    date_of_delivery = models.DateField()


class OrderItemQuantity(models.Model):
    delivery = models.ForeignKey(Delivery, on_delete=models.CASCADE)
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE)
    quantity = models.IntegerField()


class Machine(models.Model):
    name = models.CharField(max_length=32)
    shortcut = models.CharField(max_length=8)


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
