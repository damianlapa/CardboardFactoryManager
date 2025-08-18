import datetime
import math
import re
from django.db import models
from warehousemanager.models import Buyer
from django.db.models import UniqueConstraint
from django.db.models.functions import ExtractYear
from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Exists, OuterRef


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
    name = models.CharField(max_length=64, unique=True)
    price = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    dimensions = models.CharField(max_length=32, null=True, blank=True)
    flute = models.CharField(max_length=8, null=True, blank=True)
    gsm = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f'{self.name}'

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

    def total_sales(self):
        sells = ProductSell3.objects.filter(order=self)
        result = 0
        for s in sells:
            result += s.calculate_value()

        return result

    def material_cost(self):
        items = DeliveryItem.objects.filter(order=self)
        cost = 0

        for i in items:
            cost += i.calculate_value()

        return round(cost, 2)

    def production_cost(self):
        from production.models import ProductionOrder
        production_order = ProductionOrder.objects.filter(id_number=f'{self.provider} {self.order_id}').first()
        if production_order:
            return production_order.work_energy_usage_cost()
        else:
            return 0, 0, 0

    def other_costs(self):
        month, year = self.order_date.month, self.order_date.year
        month_results = MonthResults.objects.get(month=month, year=year)
        value = self.material_cost()
        expenses = month_results.expenses
        factor = value / expenses

        financial_expenses = round(month_results.financial_expenses * factor, 2)
        management_expenses = round(month_results.management_expenses * factor, 2)
        logistic_expenses = round(month_results.logistic_expenses * factor, 2)
        other_expenses = round(month_results.other_expenses * factor, 2)

        return financial_expenses, management_expenses, logistic_expenses, other_expenses

    def total_area(self):
        items = DeliveryItem.objects.filter(order=self)
        total = 0

        for item in items:
            area = item.calculate_area()
            total += area

        return int(round(total, 0))

    def check_if_settled(self):
        settlements = OrderSettlement.objects.filter(order=self)
        sales = ProductSell3.objects.filter(order=self)

        if settlements and sales:
            pieces = 0
            sold = 0
            history = WarehouseStockHistory.objects.filter(order_settlement__in=settlements, stock_supply__isnull=False)
            for h in history:
                pieces += (h.quantity_after - h.quantity_before)

            for s in sales:
                sold += s.quantity
            if pieces and sold and pieces == sold:
                return True
        return False

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
        ordering = ['-date', 'id']

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
            area = item.calculate_area()
            total += area

        return total

    def all_settle(self):
        items = DeliveryItem.objects.filter(delivery=self)
        return all([i.check_settlement() for i in items])


class DeliveryItem(models.Model):
    delivery = models.ForeignKey(Delivery, on_delete=models.PROTECT)
    order = models.ForeignKey(Order, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=0)
    palettes_quantity = models.CharField(max_length=256, blank=True, null=True)
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

        quantity_to_add = self.quantity if not quantity else quantity

        self.order.delivered_quantity += quantity_to_add
        self.order.save()

        if self.order.order_quantity:
            if self.order.delivered_quantity / self.order.order_quantity > 0.92 and not self.order.delivered:
                self.order.delivered = True
                self.order.delivery_date = self.delivery.date
                self.order.save()

        self.processed = True
        self.save()

    def check_settlement(self):
        settlement = OrderSettlement.objects.filter(order=self.order)
        return settlement

    def calculate_value(self):
        dimensions = self.order.dimensions
        price = self.order.price

        try:
            dimensions = list(map(int, dimensions.lower().strip().split('x')))
            area = dimensions[0] * dimensions[1] / 1000000
            value = area * price
            return round(self.quantity*value/1000, 2)
        except:
            return 0

    def calculate_area(self):
        try:
            dimensions = self.order.dimensions
            dimensions = dimensions.lower().split('x')
            dimensions = list(map(int, dimensions))
            area = round(dimensions[0] * dimensions[1] / 1000000, 5) * self.quantity

            return area
        except Exception as e:
            return 0


class DeliveryPalette(models.Model):
    delivery = models.ForeignKey(Delivery, on_delete=models.PROTECT)
    palette = models.ForeignKey(Palette, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f'{self.delivery} :: {self.palette} :: {self.quantity}'


class DeliverySpecial(models.Model):
    name = models.CharField(max_length=64, unique=True)
    provider = models.CharField(max_length=64)
    date = models.DateField()
    description = models.CharField(max_length=256, null=True, blank=True)
    processed = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.provider} {self.date}'

    class Meta:
        ordering = ['-date', 'id']

    def add_to_warehouse(self, warehouse=None):
        items = DeliverySpecialItem.objects.filter(delivery=self)

        for item in items:
            if not warehouse:
                warehouse = Warehouse.objects.get(name='MAGAZYN MATERIAŁÓW POMOCNICZYCH')
            item.add_to_warehouse()

        if self.check_if_processed():
            self.processed = True
            self.save()

    def check_if_processed(self):
        items = DeliverySpecialItem.objects.filter(delivery=self)
        for item in items:
            if not item.processed:
                return False
        return True

    def all_settle(self):
        items = DeliverySpecialItem.objects.filter(delivery=self)
        return all([i.check_settlement() for i in items])


class DeliverySpecialItem(models.Model):
    delivery = models.ForeignKey(DeliverySpecial, on_delete=models.PROTECT)
    name = models.CharField(max_length=64)
    quantity = models.PositiveIntegerField(default=0)
    price = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    processed = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.delivery} :: {self.name} :: {self.quantity}'

    def add_to_warehouse(self, warehouse=None, quantity=False):
        if not warehouse:
            warehouse = Warehouse.objects.get(name='MAGAZYN MATERIAŁÓW POMOCNICZYCH')

        # Create Stock Supply
        stock_supply, created = StockSupply.objects.get_or_create(
            stock_type=StockType.objects.get(stock_type='Special', unit='PIECE'),
            date=self.delivery.date,
            quantity=self.quantity,
            name=self.name
        )

        # Aktualizacja zapasów w magazynie
        stock, created = Stock.objects.get_or_create(
            name=self.name,
            stock_type=StockType.objects.get(stock_type='Special', unit='PIECE')
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

    def calculate_value(self):
        return round(self.quantity * self.price, 2)


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

    class Meta:
        ordering = ['stock__name']


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


class MonthResults(models.Model):
    month = models.PositiveIntegerField()
    year = models.PositiveIntegerField()
    expenses = models.PositiveIntegerField()
    financial_expenses = models.PositiveIntegerField()
    management_expenses = models.PositiveIntegerField()
    logistic_expenses = models.PositiveIntegerField()
    other_expenses = models.PositiveIntegerField()

    def __str__(self):
        return f'{self.year} {self.month}'


class ProductSell2(models.Model):
    order = models.ForeignKey(Order, on_delete=models.PROTECT)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=0)
    price = models.DecimalField(max_digits=5, decimal_places=2)
    date = models.DateField()

    class Meta:
        ordering = ['date']

    def __str__(self):
        return f'{self.product} {self.order} {self.quantity}'

    def calculate_value(self):
        return round(float(self.price) * float(self.quantity), 2)


class CustomerDelivery(models.Model):
    customer = models.ForeignKey(Buyer, on_delete=models.PROTECT)
    date = models.DateField()
    description = models.CharField(max_length=256, null=True, blank=True)
    palettes = models.ManyToManyField(Palette, through='DeliveryCustomerPalette', blank=True)
    items = models.ManyToManyField(ProductSell2, through='DeliverySell', blank=True)

    def __str__(self):
        return f'{self.customer} {self.date}'

    class Meta:
        ordering = ['-date']


class DeliveryCustomerPalette(models.Model):
    customer_delivery = models.ForeignKey(CustomerDelivery, on_delete=models.PROTECT)
    palette = models.ForeignKey(Palette, on_delete=models.PROTECT)
    quantity = models.IntegerField(default=0)

    def __str__(self):
        return f'{self.customer_delivery} :: {self.palette} :: {self.quantity}'


class DeliverySell(models.Model):
    customer_delivery = models.ForeignKey(CustomerDelivery, on_delete=models.PROTECT)
    item = models.ForeignKey(ProductSell2, on_delete=models.PROTECT)

    def __str__(self):
        return f'{self.customer_delivery} :: {self.item}'


class CustomerPalette(models.Model):
    customer = models.ForeignKey(Buyer, on_delete=models.PROTECT)
    palette = models.ForeignKey(Palette, on_delete=models.PROTECT)
    quantity = models.IntegerField(default=0)

    def __str__(self):
        return f'{self.customer} :: {self.palette} :: {self.quantity}'

    class Meta:
        unique_together = ['customer', 'palette']
        ordering = ['customer']


class ProductSell3(models.Model):
    customer = models.ForeignKey(Buyer, on_delete=models.PROTECT, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    warehouse_stock = models.ForeignKey(WarehouseStock, on_delete=models.PROTECT, null=True, blank=True)
    order = models.ForeignKey(Order, on_delete=models.PROTECT, null=True, blank=True)
    quantity = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    date = models.DateField()

    class Meta:
        ordering = ['date', '-customer', '-product']

    def __str__(self):
        return f'{self.product} {self.quantity} -> {self.customer}'

    def calculate_value(self):
        return round(float(self.price) * float(self.quantity), 2)

    def get_used_materials(self):
        if not self.warehouse_stock:
            return []

        results = []

        history_qs = WarehouseStockHistory.objects.filter(
            warehouse_stock=self.warehouse_stock,
            date__lte=self.date,
            order_settlement__isnull=False
        ).select_related('order_settlement__material__stock')

        for h in history_qs:
            before = h.quantity_before
            after = h.quantity_after
            delta = after - before

            if delta == 0:
                continue  # unikamy dzielenia przez zero

            if self.quantity == delta:
                ratio = 1
            else:
                ratio = self.quantity / delta

            # zaokrąglenie zużycia materiału
            used_qty = math.ceil(h.order_settlement.material_quantity * ratio)

            # nazwa materiału
            name = h.order_settlement.material.stock.name

            # wyciąganie powierzchni
            area_m2 = self._extract_area_from_name(name, used_qty)

            results.append({
                'name': name,
                'used_quantity': used_qty,
                'area_m2': area_m2
            })

        return results

    def _extract_area_from_name(self, name, quantity=1):
        """
        Szuka wzorca [długość x szerokość] w mm w nazwie materiału
        i zwraca powierzchnię w m² dla podanej liczby sztuk.
        """
        pattern = r'\[(\d+)[xX](\d+)\]'
        match = re.search(pattern, name)
        if match:
            length = int(match.group(1))  # mm
            width = int(match.group(2))  # mm
            m2 = (length / 1000) * (width / 1000)  # m² dla 1 sztuki
            return round(m2 * quantity, 2)  # m² łącznie
        return None

    def _resolve_product_from_ws(self):
        """
        Zwraca właściwy Product odpowiadający warehouse_stock.
        Preferuje FK ws.stock.product, a jeśli go nie ma — dopasowanie po nazwie.
        """
        if not self.warehouse_stock_id:
            return None
        ws = self.warehouse_stock  # zakładamy, że select_related w widoku przyspieszy dostęp
        # 1) jeśli masz FK: Stock -> Product (pole 'product')
        prod = getattr(ws.stock, "product", None)
        if prod:
            return prod
        # 2) fallback po nazwie
        return Product.objects.filter(name=ws.stock.name).first()

    def clean(self):
        # ilość dodatnia
        if self.quantity is not None and self.quantity <= 0:
            raise ValidationError({"quantity": "Ilość musi być większa od zera."})

        # cena nieujemna
        if self.price is not None and self.price < 0:
            raise ValidationError({"price": "Cena nie może być ujemna."})

        # z warehouse_stock wyciągnij produkt i/lub zweryfikuj zgodność
        if self.warehouse_stock_id:
            resolved = self._resolve_product_from_ws()
            if resolved is None:
                raise ValidationError({"warehouse_stock": "Brak produktu powiązanego z tym stanem magazynowym."})

            if self.product_id is None:
                # ustaw automatycznie
                self.product = resolved
            else:
                # sprawdź spójność, jeśli ktoś spróbuje wcisnąć inny produkt
                if self.product_id != resolved.id:
                    raise ValidationError({"product": "Wybrany produkt nie zgadza się z magazynem."})

        return super().clean()

    def save(self, *args, **kwargs):
        # zabezpieczenie na wypadek braku full_clean() w wyższych warstwach
        if self.warehouse_stock_id and self.product_id is None:
            resolved = self._resolve_product_from_ws()
            if resolved:
                self.product = resolved
        return super().save(*args, **kwargs)


class ProductComplexAssemblyQuerySet(models.QuerySet):
    def with_locked(self):
        # podzapytanie: WS użyte do PRZYJĘCIA wyrobu gotowego z tej assembly
        fg_ws_ids = WarehouseStockHistory.objects.filter(
            assembly=OuterRef("pk"),
            stock_supply__isnull=False,   # odróżnia „przyjęcie gotowca” od rozchodu części
        ).values("warehouse_stock_id")

        # locked jeśli istnieje sprzedaż z któregokolwiek z tych WS
        return self.annotate(
            _locked=Exists(
                ProductSell3.objects.filter(warehouse_stock_id__in=fg_ws_ids)
            )
        )


class ProductComplexAssembly(models.Model):
    date = models.DateField()
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.IntegerField()
    parts = models.ManyToManyField(WarehouseStock, through='ProductComplexParts', blank=True)
    objects = ProductComplexAssemblyQuerySet.as_manager()

    def __str__(self):
        return f'{self.product} {self.date} -> {self.quantity}'

    class Meta:
        ordering = ['date', 'product']

    @property
    def is_locked(self) -> bool:
        from .models import WarehouseStockHistory, ProductSell3  # jeśli w tym samym pliku, pominąć
        fg_ws_ids = WarehouseStockHistory.objects.filter(
            assembly=self, stock_supply__isnull=False
        ).values_list("warehouse_stock_id", flat=True)
        if not fg_ws_ids:
            return False
        return ProductSell3.objects.filter(warehouse_stock_id__in=fg_ws_ids).exists()

    def clean(self):
        # blokada modyfikacji/rozbiórki po sprzedaży
        if self.pk and self.is_locked:
            raise ValidationError("Nie można modyfikować: wyrób z tego montażu został sprzedany.")
        return super().clean()

    def save(self, *args, **kwargs):
        # przy aktualizacji wymuś walidację -> zadziała blokada
        if self.pk:
            self.full_clean()
        return super().save(*args, **kwargs)


class ProductComplexParts(models.Model):
    assembly = models.ForeignKey(ProductComplexAssembly, on_delete=models.PROTECT, related_name="assembly_parts")
    part = models.ForeignKey(WarehouseStock, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f'{self.part} :: {self.quantity}'

    class Meta:
        ordering = ['assembly', 'part']


class WarehouseStockHistory(models.Model):
    warehouse_stock = models.ForeignKey(WarehouseStock, on_delete=models.CASCADE, related_name="warehouse_stock")
    stock_supply = models.ForeignKey(StockSupply, on_delete=models.PROTECT, null=True, blank=True)
    order_settlement = models.ForeignKey(OrderSettlement, on_delete=models.PROTECT, null=True, blank=True)
    assembly = models.ForeignKey(ProductComplexAssembly, on_delete=models.PROTECT, null=True, blank=True)
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
        elif self.assembly:
            return f'{self.date} | {self.warehouse_stock.stock.name} DECREASE {self.quantity_before} -> {self.quantity_after}'
        else:
            return f'{self.date} | {self.warehouse_stock.stock.name} DECREASE {self.quantity_before} -> {self.quantity_after}'