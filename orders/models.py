from django.db import models
from warehousemanager.models import Buyer

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

ORDER_STATUSES = (
    ("FINISHED", 'FINISHED'),
    ('ACCEPTED', 'ACCEPTED'),
    ('IN PROGRESS', 'IN PROGRESS'),
    ('NOT STARTED', 'NOT STARTED')
)


'''class Supplier(models.Model):
    name = models.CharField(max_length=64, unique=True)
    shortcut = models.CharField(max_length=8, unique=True)

    def __str__(self):
        return f'{self.name}({self.shortcut})'


class Cardboard(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT)
    designation = models.CharField(max_length=16)
    layers = models.CharField(max_length=1, choices=CARDBOARD_LAYERS)
    wave = models.CharField(max_length=8, choices=CARDBOARD_TYPES)
    grammage = models.IntegerField()
    ect = models.DecimalField(max_digits=4, decimal_places=2)

    def __str__(self):
        return f'{self.supplier.shortcut}|{self.designation}|{self.grammage}|{self.ect}'


class Product(models.Model):
    type = models.CharField(max_length=64, choices=PRODUCT_TYPES)
    description = models.CharField(max_length=256, default="")
    dimensions = models.CharField(max_length=128, blank=True, null=True)
    cardboard = models.ForeignKey(Cardboard, on_delete=models.PROTECT, null=True)

    def __str__(self):
        return f'{self.type} {self.dimensions} {self.cardboard}'


class ProductPrice(models.Model):
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    price = models.DecimalField(max_digits=6, decimal_places=3)

    def __str__(self):
        return f'{self.product} - {self.price}'


class ProductSell(models.Model):
    product_price = models.ForeignKey(ProductPrice, on_delete=models.PROTECT)
    customer = models.ForeignKey(Buyer, on_delete=models.PROTECT)
    quantity = models.IntegerField()
    date = models.DateField()


class CardboardPurchase(models.Model):
    date = models.DateField()
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT)
    cardboard = models.ForeignKey(Cardboard, on_delete=models.PROTECT)
    dimensions = models.CharField(max_length=16)
    ordered_quantity = models.IntegerField()
    delivered_quantity = models.IntegerField(blank=True, null=True)
    price_1000 = models.IntegerField()

    def __str__(self):
        return f'{self.cardboard} - {self.ordered_quantity}'
'''

'''

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
'''


class Customer(models.Model):
    name = models.CharField(max_length=128, unique=True)
    shortcut = models.CharField(max_length=8, unique=True)

    def __str__(self):
        return f'{self.name}({self.shortcut})'


class Product(models.Model):
    name = models.CharField(max_length=64)
    product_type = models.CharField(max_length=64, choices=PRODUCT_TYPES)

    def __str__(self):
        return f'{self.product_type} - {self.name}'


class Order(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT)
    date = models.DateField()
    deadline = models.DateField()
    status = models.CharField(max_length=32, choices=ORDER_STATUSES, default='NOT STARTED')

    def __str__(self):
        return f'{self.customer}({self.date})[{self.id}]'


class OrderProduct(models.Model):
    order = models.ForeignKey(Order, on_delete=models.PROTECT)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    deadline = models.DateField(null=True, blank=True)
    cardboard = models.BooleanField(default=False)
    realized = models.BooleanField(default=False)

    def time_to_realize(self):
        deadline = self.deadline if self.deadline else self.order.deadline
        difference = deadline - datetime.date.today()
        return difference.days


class Delivery(models.Model):
    date = models.DateField()
    quantity = models.PositiveIntegerField()

