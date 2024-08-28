from django.db import models
from warehousemanager.models import Buyer, Person


class CustomerDetails(models.Model):
    customer = models.OneToOneField(Buyer, on_delete=models.PROTECT)
    representative = models.ForeignKey(Person, on_delete=models.PROTECT, null=True, blank=True)
    full_name = models.CharField(max_length=128, null=True, blank=True)
    tax_number = models.CharField(max_length=32, null=True, blank=True)
    country = models.CharField(max_length=32, default='POLAND')
    city = models.CharField(max_length=32, null=True, blank=True)
    zip_code = models.CharField(max_length=8, null=True, blank=True)
    address = models.CharField(max_length=32, null=True, blank=True)
    date_add = models.DateTimeField(auto_now_add=True)
    date_edit = models.DateTimeField(auto_now=True)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return f'{self.customer.name}'


class Note(models.Model):
    date_add = models.DateTimeField(auto_now_add=True)
    date = models.DateField(null=True, blank=True)
    customer = models.ForeignKey(CustomerDetails, on_delete=models.PROTECT)
    description = models.TextField()

    def __str__(self):
        return f'{self.customer} {self.date}'


class Order(models.Model):
    date_add = models.DateTimeField(auto_now_add=True)
    date = models.DateField(null=True, blank=True)
    customer = models.ForeignKey(CustomerDetails, on_delete=models.PROTECT)
    description = models.TextField()

    def __str__(self):
        return f'{self.customer} {self.date}'


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.PROTECT)
    date = models.DateField()
    item = models.CharField(max_length=64, null=True, blank=True)
    name = models.CharField(max_length=64, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=0)
    cardboard = models.CharField(max_length=16, null=True, blank=True)
    area = models.DecimalField(max_digits=7, decimal_places=2)
