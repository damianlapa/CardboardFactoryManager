from django.db import models
from warehousemanager.models import Person
from orders.models import OrderProduct


EVENT_TYPES = (
    ('PLANOWANA DOSTAWA', 'PLANOWANA DOSTAWA'),
    ('ZREALIZOWANA DOSTAWA', 'ZREALIZOWANA DOSTAWA'),
    ('SPOTKANIE', 'SPOTKANIE'),
    ('ODBIÓR OSOBISTY', 'ODBIÓR OSOBISTY'),
    ('INNE', 'INNE')
)


class Event(models.Model):
    event_type = models.CharField(max_length=32, choices=EVENT_TYPES)
    title = models.CharField(max_length=64)
    day = models.DateField()
    details = models.TextField(blank=True, null=True)

    def __str__(self):
        return f'{self.day}) {self.title}'


class Provider(models.Model):
    name = models.CharField(max_length=128)
    shortcut = models.CharField(max_length=16)


class Delivery(models.Model):
    date = models.DateField()
    provider = models.ForeignKey(Provider, on_delete=models.PROTECT)
    car_number = models.CharField(max_length=32, null=False)
    driver = models.CharField(max_length=64, null=False)
    phone = models.CharField(max_length=24, null=False)
    palette_number = models.PositiveIntegerField(default=0)
    worker = models.ForeignKey(Person, on_delete=models.PROTECT)


class DeliveryItem(models.Model):
    delivery = models.ForeignKey(Delivery, on_delete=models.PROTECT)
    order_item = models.ForeignKey(OrderProduct, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()

