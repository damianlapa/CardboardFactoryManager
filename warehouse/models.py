from django.db import models
from warehousemanager.models import Buyer
from django.db.models import UniqueConstraint
from django.db.models.functions import ExtractYear


UNITS = (
    ('KG', 'KG'),
    ('M2', 'M2'),
    ('PIECE', 'PIECE'),
    ('SET', 'SET')
)


class Palette(models.Model):
    name = models.CharField(max_length=32)

    def __str__(self):
        return f'{self.name}'


class Provider(models.Model):
    name = models.CharField(max_length=64)
    shortcut = models.CharField(max_length=24, null=True, blank=True)

    def __str__(self):
        return f'{self.name}'


class Product(models.Model):
    name = models.CharField(max_length=64)
    price = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)

    def __str__(self):
        return f'{self.name}'

    class Meta:
        ordering = ['name']


class Order(models.Model):
    customer = models.ForeignKey(Buyer, on_delete=models.PROTECT)
    provider = models.ForeignKey(Provider, on_delete=models.PROTECT)
    order_id = models.CharField(max_length=32)
    customer_date = models.DateField()
    order_date = models.DateField(null=True, blank=True)
    delivery_date = models.DateField(null=True, blank=True)
    production_date = models.DateField(null=True, blank=True)
    dimensions = models.CharField(max_length=32)
    name = models.CharField(max_length=32)
    weight = models.PositiveIntegerField(default=0)
    order_quantity = models.PositiveIntegerField()
    delivered_quantity = models.PositiveIntegerField(default=0)
    price = models.PositiveIntegerField(default=0)
    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.PROTECT)
    delivered = models.BooleanField(default=False)
    finished = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.provider} {self.order_id} {self.name}'

    class Meta:
        ordering = ['order_date', 'provider', 'order_id']


class Delivery(models.Model):
    provider = models.ForeignKey(Provider, on_delete=models.PROTECT)
    date = models.DateField()
    car_number = models.CharField(max_length=16, null=True, blank=True)
    telephone = models.CharField(max_length=16, null=True, blank=True)
    description = models.CharField(max_length=256, null=True, blank=True)
    palettes = models.ManyToManyField(Palette, through='DeliveryPalette', blank=True)

    def __str__(self):
        return f'{self.provider}({self.car_number}) {self.date}'


class DeliveryItem(models.Model):
    delivery = models.ForeignKey(Delivery, on_delete=models.PROTECT)
    order = models.ForeignKey(Order, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=0)
    palettes_quantity = models.CharField(max_length=128, blank=True, null=True)

    def __str__(self):
        return f'{self.delivery} :: {self.order}'


class DeliveryPalette(models.Model):
    delivery = models.ForeignKey(Delivery, on_delete=models.PROTECT)
    palette = models.ForeignKey(Palette, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f'{self.delivery} :: {self.palette} :: {self.quantity}'


class StockType(models.Model):
    _type = models.CharField(max_length=64)
    unit = models.CharField(max_length=16, choices=UNITS)

    def __str__(self):
        return f'{self._type} [{self.unit}]'


class StockSupply(models.Model):
    stock_type = models.ForeignKey(StockType, on_delete=models.PROTECT)
    provider = models.ForeignKey(Provider, on_delete=models.PROTECT)
    dimensions = models.CharField(max_length=32, null=True, blank=True)
    weight = models.PositiveIntegerField(null=True, blank=True)
    date = models.DateField(null=True, blank=True)
    quantity = models.PositiveIntegerField(default=0)
    name = models.CharField(max_length=64)


class Stock(models.Model):
    stock_type = models.ForeignKey(StockType, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=0)
    name = models.CharField(max_length=64)
    supplies = models.ManyToManyField(StockSupply, blank=True)

    def __str__(self):
        return f'{self.stock_type._type}: {self.quantity} {self.stock_type.unit}'

    def update_stock(self, supply: StockSupply):
        if supply not in self.supplies.all():
            self.supplies.add(supply)
            self.quantity += supply.quantity
            self.save()

    def __decrease_stock(self, supply: StockSupply):
        if supply not in self.supplies.all():
            self.supplies.remove(supply)
            self.quantity -= supply.quantity
            self.save()


class Warehouse(models.Model):
    name = models.CharField(max_length=64)
    stocks = models.ManyToManyField(Stock, blank=True)

    def __str__(self):
        return f'{self.name}'
