from django.db import models
from warehousemanager.models import Buyer, Person


class CustomerDetails(models.Model):
    customer = models.ForeignKey(Buyer, on_delete=models.PROTECT)
    representative = models.ForeignKey(Person, on_delete=models.PROTECT, null=True, blank=True)
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

