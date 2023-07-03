from django.db import models

import datetime


PRODUCT_TYPES = (
    ('Karton', 'Karton'),
    ('Przekładka', 'Przekładka'),
    ('Taśma', 'Taśma'),
    ('Folia Stretch', 'Folia Stretch'),
    ('Folia Bąbelkowa', 'Folia Bąbelkowa'),
    ('Usługa', 'Usługa'),
    ('Paleta', 'Paleta'),
    ('Produkt', 'Produkt')
)


CARDBOARD_TYPES = (
    ('A', 'A'),
    ('B', 'B'),
    ('C', 'C'),
    ('D', 'D'),
    ('E', 'E'),
    ('F', 'F'),
    ('BC', 'BC'),
    ('EB', 'EB'),
    ('EC', 'EC'),
    ('EE', 'EE')
)


CARDBOARD_LAYERS = (
    ('2', '2'),
    ('3', '3'),
    ('4', '4'),
    ('5', '5'),
    ('6', '6'),
    ('7', '7')
)


class Supplier(models.Model):
    name = models.CharField(max_length=64)
    shortcut = models.CharField(max_length=8)

    def __str__(self):
        return f'{self.shortcut}'


'''class Cardboard(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT)
    designation = models.CharField(max_length=16)
    layers = models.CharField(max_length=1, choices=CARDBOARD_LAYERS)
    wave = models.CharField(max_length=8, choices=CARDBOARD_TYPES)
    grammage = models.IntegerField()

    def __str__(self):
        return f'{self.supplier.shortcut}|{self.designation}|{self.grammage}|{self.ect}'


class Customer(models.Model):
    name = models.CharField(max_length=128, unique=True)
    shortcut = models.CharField(max_length=32, unique=True)

    def __str__(self):
        return f'{self.name}({self.shortcut})'


class Order(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT)
    date = models.DateField()
    number = models.CharField(max_length=32, default='', blank=True, null=True)

    def __str__(self):
        return f'{self.customer} - {self.date}'



class Product(models.Model):
    type = models.CharField(max_length=64, choices=PRODUCT_TYPES)
    description = models.CharField(max_length=256, default="")
    dimensions = models.CharField(max_length=128, blank=True, null=True)
    cardboard = models.ForeignKey(Cardboard, on_delete=models.PROTECT, null=True)

    def __str__(self):
        return f'{self.type} {self.dimensions} {self.cardboard}'



class OrderUnit(models.Model):
    order = models.ForeignKey(Order, on_delete=models.PROTECT)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.IntegerField()
    delivered = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.order.customer} | {self.product} | {self.quantity}'


class Delivery(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT)
    date = models.DateField()

    def __str__(self):
        return f'{self.supplier} {self.date}'


class DeliveryUnit(models.Model):
    delivery = models.ForeignKey(Delivery, on_delete=models.PROTECT)
    order_unit = models.ForeignKey(OrderUnit, on_delete=models.PROTECT)
    quantity = models.IntegerField()

    def __str__(self):
        return f'{self.delivery} {self.order_unit.order.customer} {self.order.product} q:{self.quantity}'


class CardboardPurchase(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT)
    cardboard = models.ForeignKey(Cardboard, on_delete=models.PROTECT)
    dimensions = models.CharField(max_length=16)
    ordered_quantity = models.IntegerField()
    delivered_quantity = models.IntegerField(blank=True, null=True)
    price_1000 = models.IntegerField()

    def __str__(self):
        return f'{self.cardboard} - {self.ordered_quantity}'''
