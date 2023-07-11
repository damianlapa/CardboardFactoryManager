from django.db import models

RESOURCE_TYPES = (
    ('CARDBOARD', 'CARDBOARD'),
    ('PACKAGING TAPE', 'PACKAGING TAPE'),
    ('STRETCH FOIL', 'STRETCH FOIL'),
    ('GLUE', 'GLUE'),
    ('BINDING TAPE', 'BINDING TAPE'),
    ('OTHERS', 'OTHERS'),

)

RESOURCE_UNITS = (
    ('PIECE', 'PIECE'),
    ('KG', 'KG'),
    ('M2', 'M2'),
    ('HOUR', 'HOUR')
)

PRODUCT_TYPES = (
    ('BOX', 'BOX'),

)


class Customer(models.Model):
    name = models.CharField(max_length=128)
    tax_number = models.CharField(max_length=10, unique=True)
    description = models.CharField(max_length=512, null=True, blank=True)

    def __str__(self):
        return f'{self.name}'


class Resource(models.Model):
    name = models.CharField(max_length=64)
    resource_type = models.CharField(max_length=32, choices=RESOURCE_TYPES)
    unit = models.CharField(max_length=32, choices=RESOURCE_UNITS)
    quantity = models.DecimalField(max_digits=9, decimal_places=2)
    price = models.DecimalField(max_digits=12, decimal_places=3)
    date = models.DateField()
    used = models.BooleanField(default=False)
    description = models.CharField(max_length=256, blank=True, null=True)

    def __str__(self):
        return f'{self.name} [{self.resource_type}] : {self.quantity} {self.unit}'


class Expense(models.Model):
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField()
    title = models.CharField(max_length=64)
    description = models.CharField(max_length=248, null=True, blank=True)

    def __str__(self):
        return f'{self.title} | {self.date} | {self.amount}'


class Product(models.Model):
    name = models.CharField(max_length=64, unique=True)
    product_type = models.CharField(max_length=32, choices=PRODUCT_TYPES)
    quantity = models.IntegerField(default=0)
    description = models.CharField(max_length=248, null=True, blank=True)

    def __str__(self):
        return f'{self.name}: {self.quantity}'


class ProductSell(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.IntegerField()
    price_per_unit = models.DecimalField(max_digits=12, decimal_places=3)
    date = models.DateField()

    def __str__(self):
        return f'{self.product.name} -> {self.customer.name} : {self.quantity}'


class ProductProduction(models.Model):
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    resources = models.ManyToManyField(Resource, through='ProductResourceProduction')
    date = models.DateField()
    quantity = models.IntegerField()

    def __str__(self):
        return f'{self.product.name} ({self.date}) {self.quantity}'


class ProductResourceProduction(models.Model):
    product_production = models.ForeignKey(ProductProduction, on_delete=models.PROTECT)
    resource = models.ForeignKey(Resource, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=9, decimal_places=2)

    def __str__(self):
        return f'{self.product_production} | {self.resource} | {self.quantity}'






