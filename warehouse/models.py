import datetime

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
    dimensions = models.CharField(max_length=32, null=True, blank=True)
    flute = models.CharField(max_length=8, null=True, blank=True)
    gsm = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f'{self.name} {self.dimensions}'

    class Meta:
        ordering = ['name']


class Order(models.Model):
    customer = models.ForeignKey(Buyer, on_delete=models.PROTECT)
    provider = models.ForeignKey(Provider, on_delete=models.PROTECT)
    order_id = models.CharField(max_length=32, unique=False)
    customer_date = models.DateField()
    order_date = models.DateField(null=True, blank=True)
    order_year = models.CharField(max_length=4, null=True, blank=True)
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
    updated = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.provider} {self.order_id} {self.name}'

    class Meta:
        ordering = ['order_date', 'provider', 'order_id']
        unique_together = ('provider', 'order_id', 'order_year')


class Delivery(models.Model):
    number = models.CharField(max_length=64, unique=True)
    provider = models.ForeignKey(Provider, on_delete=models.PROTECT)
    date = models.DateField()
    car_number = models.CharField(max_length=16, null=True, blank=True)
    telephone = models.CharField(max_length=16, null=True, blank=True)
    description = models.CharField(max_length=256, null=True, blank=True)
    palettes = models.ManyToManyField(Palette, through='DeliveryPalette', blank=True)
    processed = models.BooleanField(default=False)
    updated = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.provider}({self.car_number}) {self.date}'

    class Meta:
        ordering = ['-date']

    def add_to_warehouse(self, warehouse=None):
        items = DeliveryItem.objects.filter(delivery=self)

        for item in items:
            if not warehouse:
                warehouse = Warehouse.objects.get(name='MAGAZYN GŁÓWNY')
            item.add_to_warehouse()

        if self.check_if_processed():
            self.processed = True
            self.save()

    def check_if_processed(self):
        items = DeliveryItem.objects.filter(delivery=self)
        for item in items:
            if not item.processed:
                return False
        return True

    def count_area(self):
        items = DeliveryItem.objects.filter(delivery=self)
        total = 0

        for item in items:
            dimensions = item.order.dimensions
            dimensions = dimensions.lower().split('x')
            dimensions = list(map(int, dimensions))
            area = round(dimensions[0]*dimensions[1]/1000000, 5) * item.quantity
            total += area

        return total

    def all_settle(self):
        items = DeliveryItem.objects.filter(delivery=self)
        return all([i.check_settlement() for i in items])


class DeliveryItem(models.Model):
    delivery = models.ForeignKey(Delivery, on_delete=models.PROTECT)
    order = models.ForeignKey(Order, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=0)
    palettes_quantity = models.CharField(max_length=128, blank=True, null=True)
    processed = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.delivery} :: {self.order}'

    def add_to_warehouse(self, warehouse=None, quantity=False):
        if not warehouse:
            warehouse = Warehouse.objects.get(name='MAGAZYN GŁÓWNY')

        # Create Stock Supply
        stock_supply, created = StockSupply.objects.get_or_create(
            stock_type=StockType.objects.get(stock_type='Material', unit='PIECE'),
            delivery_item=self,
            date=self.delivery.date,
            dimensions=self.order.dimensions,
            quantity=self.quantity,
            name=f'{self.order.name}[{self.order.dimensions}]'
        )

        # Aktualizacja zapasów w magazynie
        stock, created = Stock.objects.get_or_create(
            name=f'{self.order.name}[{self.order.dimensions}]',
            stock_type=StockType.objects.get(stock_type='Material', unit='PIECE')
        )
        warehouse_stock, created = WarehouseStock.objects.get_or_create(warehouse=warehouse, stock=stock)

        history, created = WarehouseStockHistory.objects.get_or_create(
            warehouse_stock=warehouse_stock,
            stock_supply=stock_supply,
            quantity_before=warehouse_stock.quantity,
            quantity_after=warehouse_stock.quantity+self.quantity

        )

        warehouse_stock.increase_quantity(self.quantity if not quantity else quantity)

        self.processed = True
        self.save()

    def check_settlement(self):
        settlement = OrderSettlement.objects.filter(order=self.order)
        return settlement


class DeliveryPalette(models.Model):
    delivery = models.ForeignKey(Delivery, on_delete=models.PROTECT)
    palette = models.ForeignKey(Palette, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f'{self.delivery} :: {self.palette} :: {self.quantity}'


class StockType(models.Model):
    stock_type = models.CharField(max_length=64)
    unit = models.CharField(max_length=16, choices=UNITS)

    def __str__(self):
        return f'{self.stock_type} [{self.unit}]'

    def get_stock_type(self):
        return f'{self.stock_type}'


class StockSupply(models.Model):
    stock_type = models.ForeignKey(StockType, on_delete=models.PROTECT)
    delivery_item = models.ForeignKey(DeliveryItem, on_delete=models.PROTECT, null=True, blank=True)
    dimensions = models.CharField(max_length=32, null=True, blank=True)
    date = models.DateField(null=True, blank=True)
    quantity = models.PositiveIntegerField(default=0)
    name = models.CharField(max_length=64)


class Stock(models.Model):
    stock_type = models.ForeignKey(StockType, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=0)
    name = models.CharField(max_length=64)

    def __str__(self):
        return f'{self.stock_type.stock_type}: {self.name}'

    def update_stock(self, supply_quantity):
        self.quantity += supply_quantity
        self.save()

    def __decrease_stock(self, supply: StockSupply):
        if supply not in self.supplies.all():
            self.supplies.remove(supply)
            self.quantity -= supply.quantity
            self.save()


class Warehouse(models.Model):
    name = models.CharField(max_length=64)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return f'{self.name}'

    def add_stock(self, stock, quantity):
        warehouse_stock, created = WarehouseStock.objects.get_or_create(warehouse=self, stock=stock)
        warehouse_stock.increase_quantity(quantity)


class WarehouseStock(models.Model):
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='warehouse_stocks')
    stock = models.ForeignKey("Stock", on_delete=models.CASCADE, related_name='warehouse_stocks')
    quantity = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f'{self.stock.name} in {self.warehouse.name}: {self.quantity}'

    def increase_quantity(self, quantity):
        self.quantity += quantity
        self.save()

    def decrease_quantity(self, quantity):
        if quantity > self.quantity:
            raise ValueError("Cannot decrease quantity below zero.")
        self.quantity -= quantity
        self.save()


# <-- rozbudowa modeli
class OrderSettlement(models.Model):
    order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='settlements')
    material = models.ForeignKey(WarehouseStock, on_delete=models.PROTECT, related_name='used_in_settlements')
    material_quantity = models.PositiveIntegerField(default=0)
    settlement_date = models.DateField(default=datetime.date.today)

    def __str__(self):
        return f"Settlement for Order {self.order.order_id} on {self.settlement_date}"


class OrderSettlementProduct(models.Model):
    settlement = models.ForeignKey(OrderSettlement, on_delete=models.CASCADE, related_name='settlement_products')
    stock_supply = models.ForeignKey('StockSupply', on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=0)
    is_semi_product = models.BooleanField(default=False)  # True dla półproduktów

    def __str__(self):
        return f"{self.stock_supply.name} ({self.quantity}) - {'Semi-Product' if self.is_semi_product else 'Product'}"


class WarehouseStockHistory(models.Model):
    warehouse_stock = models.ForeignKey(WarehouseStock, on_delete=models.CASCADE, related_name="warehouse_stock")
    stock_supply = models.ForeignKey(StockSupply, on_delete=models.PROTECT, null=True, blank=True)
    order_settlement = models.ForeignKey(OrderSettlement, on_delete=models.PROTECT, null=True, blank=True)
    quantity_before = models.PositiveIntegerField(default=0)
    quantity_after = models.PositiveIntegerField(default=0)
    date = models.DateField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.date:
            if self.stock_supply:
                self.date = self.stock_supply.date
            elif self.order_settlement:
                self.date = self.order_settlement.settlement_date
        super().save(*args, **kwargs)

    def __str__(self):
        if self.stock_supply:
            return f'{self.date} | {self.warehouse_stock.stock.name} INCREASE {self.quantity_before} -> {self.quantity_after}'
        elif self.order_settlement:
            return f'{self.date} | {self.warehouse_stock.stock.name} DECREASE {self.quantity_before} -> {self.quantity_after}'
        else:
            return f'{self.date} | {self.warehouse_stock.stock.name} DECREASE {self.quantity_before} -> {self.quantity_after}'


class ProductSell(models.Model):
    warehouse_stock = models.ForeignKey(WarehouseStock, on_delete=models.PROTECT, null=True, blank=True)
    quantity = models.IntegerField(default=1)
    customer = models.ForeignKey(Buyer, on_delete=models.PROTECT, null=True, blank=True)
    price = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    date = models.DateField()

    def __str__(self):
        return f'{self.date} :: {self.warehouse_stock} - {self.customer} - {self.quantity}'

    @property
    def total_value(self):
        return self.quantity * self.price

