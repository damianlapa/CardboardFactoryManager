from django.db import models


UNITS = (
    ('KG', 'KG'),
    ('M2', 'M2'),
    ('PIECE', 'PIECE'),
    ('SET', 'SET')
)


class Provider(models.Model):
    name = models.CharField(max_length=64)
    shortcut = models.CharField(max_length=24, null=True, blank=True)

    def __str__(self):
        return f'{self.name}'


class StockType(models.Model):
    _type = models.CharField(max_length=64)
    unit = models.CharField(max_length=16, choices=UNITS)

    def __str__(self):
        return f'{self._type} [{self.unit}]'


class StockSupply(models.Model):
    stock_type = models.ForeignKey(StockType, on_delete=models.PROTECT)
    provider = models.ForeignKey(Provider, on_delete=models.PROTECT)
    date = models.DateField(null=True, blank=True)
    quantity = models.PositiveIntegerField(default=0)
    name = models.CharField(max_length=64)


class Stock(models.Model):
    stock_type = models.ForeignKey(StockType, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=0)
    name = models.CharField(max_length=64)
    supplies = models.ManyToManyField(StockSupply)

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
    stocks = models.ManyToManyField(Stock)

    def __str__(self):
        return f'{self.name}'
