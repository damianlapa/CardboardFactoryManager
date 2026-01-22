import datetime
import math
import re
from warehousemanager.models import Buyer
from django.db.models import Exists, OuterRef
from django.db.models import Sum
from decimal import Decimal, ROUND_HALF_UP
from utils.money import money, D, money_sum
from django.db import models, transaction
from django.core.exceptions import ValidationError


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
    price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
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
    default_pieces = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("1.00"))
    order_quantity = models.PositiveIntegerField()
    delivered_quantity = models.PositiveIntegerField(default=0)
    price = models.PositiveIntegerField(default=0)
    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.PROTECT)
    delivered = models.BooleanField(default=False)
    finished = models.BooleanField(default=False)
    updated = models.BooleanField(default=False)
    bom = models.ForeignKey("BOM", on_delete=models.PROTECT, null=True, blank=True, related_name="orders")

    def __str__(self):
        return f'{self.provider} {self.order_id} {self.name}'

    def total_sales(self):
        sells = ProductSell3.objects.filter(order=self)
        return money_sum(s.calculate_value() for s in sells)

    def material_cost(self):
        orders_from = OrderToOrderShift.objects.filter(order_from=self)
        orders_to = OrderToOrderShift.objects.filter(order_to=self)
        items = DeliveryItem.objects.filter(order=self)
        cost = Decimal('0.00')

        for i in items:
            value = i.calculate_value() if i.calculate_value() is not None else Decimal('0')
            cost += value

        for of in orders_from:
            cost -= Decimal(of.get_value())

        for ot in orders_to:
            cost += Decimal(ot.get_value())

        return cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def production_cost(self):
        from production.models import ProductionOrder
        production_order = ProductionOrder.objects.filter(id_number=f'{self.provider} {self.order_id}').first()
        if production_order:
            return production_order.work_energy_usage_cost()
        else:
            return Decimal('0.00'), Decimal('0.00'), Decimal('0.00')

    def other_costs(self):
        month, year = self.order_date.month, self.order_date.year
        month_results = MonthResults.objects.get(month=month, year=year)

        value = D(self.material_cost())
        expenses = D(month_results.expenses)

        if expenses == 0:
            return money(0), money(0), money(0), money(0)

        factor = value / expenses

        financial = money(D(month_results.financial_expenses) * factor)
        management = money(D(month_results.management_expenses) * factor)
        logistic = money(D(month_results.logistic_expenses) * factor)
        other = money(D(month_results.other_expenses) * factor)

        return financial, management, logistic, other

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

    def check_material_usage(self):
        settlements = OrderSettlement.objects.filter(order=self)
        for s in settlements:
            print(s)

    class Meta:
        ordering = ['order_date', 'provider', 'order_id']
        unique_together = ('provider', 'order_id', 'order_year')


class OrderToOrderShift(models.Model):
    date = models.DateField()
    order_from = models.ForeignKey(Order, related_name='shifts_from', on_delete=models.PROTECT)
    order_to = models.ForeignKey(Order, related_name='shifts_to', on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return f'{self.order_from.order_id} -> {self.order_to.order_id} :: {self.quantity}'

    def get_value(self):
        items = DeliveryItem.objects.filter(order=self.order_from)
        if not items:
            return money(0)
        one_piece_value = items[0].calculate_piece_value()
        return money(D(one_piece_value) * D(self.quantity))

    def get_items(self):
        items = []

        s_items = DeliveryItem.objects.filter(order=self.order_from)
        if s_items:
            items.append(s_items[0])

        stock_supplies = StockSupply.objects.filter(delivery_item__in=items)
        stock_materials = []
        for stock_supply in stock_supplies:
            try:
                stock = Stock.objects.get(name=stock_supply.name)
                warehouse_stock = WarehouseStock.objects.get(stock=stock)
                if warehouse_stock not in stock_materials:
                    stock_materials.append(warehouse_stock)

            except Exception as e:
                pass

        return stock_materials


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
            if not item.processed:
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
    updated = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.delivery} :: {self.order}'

    def add_to_warehouse(self, warehouse=None, quantity=False):
        if not warehouse:
            warehouse = Warehouse.objects.get(name='MAGAZYN GŁÓWNY')

        # Create Stock Supply
        stock_supply, created = StockSupply.objects.get_or_create(
            stock_type=StockType.objects.get(stock_type='material', unit='PIECE'),
            delivery_item=self,
            date=self.delivery.date,
            dimensions=self.order.dimensions,
            quantity=self.quantity,
            name=f'{self.order.name}[{self.order.dimensions}]',
            value=self.calculate_value()
        )

        # Aktualizacja zapasów w magazynie
        stock, created = Stock.objects.get_or_create(
            name=f'{self.order.name}[{self.order.dimensions}]',
            stock_type=StockType.objects.get(stock_type='material', unit='PIECE')
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

    def calculate_piece_value(self):
        try:
            dims = list(map(int, self.order.dimensions.lower().strip().split('x')))
            area_m2 = (Decimal(dims[0]) * Decimal(dims[1])) / Decimal("1000000")
            price = Decimal(self.order.price)  # u Ciebie price jest intem
            value = (area_m2 * price) / Decimal("1000")
            return value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)  # dokładniej za sztukę
        except:
            return Decimal("0")

    def calculate_value(self):
        value = self.calculate_area() * self.order.price / 1000
        return money(value)

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
            if not warehouse and not item.warehouse:
                warehouse = Warehouse.objects.get(name='MAGAZYN MATERIAŁÓW POMOCNICZYCH')
            elif item.warehouse:
                warehouse = item.warehouse
            item.add_to_warehouse(warehouse=warehouse)

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
    price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    processed = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.delivery} :: {self.name} :: {self.quantity}'

    def save(self, *args, **kwargs):
        if self.name:
            self.name = self.name.strip()
        super().save(*args, **kwargs)

    def calculate_value(self):
        return money(D(self.price) * D(self.quantity))

    def add_to_warehouse(self, warehouse=None, quantity=False):
        if not warehouse:
            warehouse = Warehouse.objects.get(name='MAGAZYN MATERIAŁÓW POMOCNICZYCH')
            if 'gotowe' in str(self.delivery.name).lower():
                warehouse = Warehouse.objects.get(name='MAGAZYN WYROBÓW GOTOWYCH')
            elif 'wyprzedażowe' in str(self.delivery.name).lower():
                warehouse = Warehouse.objects.get(name='MAGAZYN WYPRZEDAŻOWY')

        # Create Stock Supply
        stock_supply, created = StockSupply.objects.get_or_create(
            stock_type=StockType.objects.get(stock_type='special', unit='PIECE'),
            date=self.delivery.date,
            quantity=self.quantity,
            name=self.name,
            value=self.calculate_value()
        )

        # Aktualizacja zapasów w magazynie
        stock, created = Stock.objects.get_or_create(
            name=self.name,
            stock_type=StockType.objects.get(stock_type='special', unit='PIECE')
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
    used = models.BooleanField(default=False)
    value = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f'[{self.date}] {self.dimensions} {self.name}'

    def piece_value(self):
        return money(D(self.value) / D(self.quantity)) if self.quantity else money(0)



class Stock(models.Model):
    stock_type = models.ForeignKey(StockType, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=0)
    name = models.CharField(max_length=64)

    class Meta:
        ordering = ['stock_type__stock_type', 'name']

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

    def count_warehouse_value(self):
        stocks = WarehouseStock.objects.filter(warehouse=self, quantity__gt=0)
        value = 0
        for s in stocks:
            value += s.count_value()
        return value


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

    def count_value(self):
        supplies_sum = (
                StockSupply.objects
                .filter(name=self.stock.name, used=False)
                .aggregate(total=Sum('value'))
                .get('total') or Decimal('0')
        )

        settlements_sum = (
                StockSupplySettlement.objects
                .filter(stock_supply__name=self.stock.name)
                .aggregate(total=Sum('value'))
                .get('total') or Decimal('0')
        )

        return supplies_sum - settlements_sum

    @staticmethod
    def use_specified_stock_supply(order_settlement, quantity: int):
        with transaction.atomic():
            order = order_settlement.order
            stock_supplies = StockSupply.objects.filter(delivery_item__order=order, used=False)
            if not stock_supplies:
                raise Exception('No stock supplies for this order')
            stock_supplies_quantity = 0
            for s in stock_supplies:
                stock_supplies_quantity += s.quantity
                stock_supply_settlements = StockSupplySettlement.objects.filter(stock_supply=s)
                for sss in stock_supply_settlements:
                    stock_supplies_quantity -= sss.quantity
            if stock_supplies_quantity < quantity:
                raise Exception('There is not enough material')
            if stock_supplies_quantity == quantity:
                value = 0
                for s in stock_supplies:
                    StockSupplySettlement.objects.create(
                        settlement=order_settlement, stock_supply=s, quantity=s.quantity
                    )
                    value += s.value
                    s.used = True
                    s.save()
                return True, value
            elif stock_supplies_quantity > quantity:
                quantity_left = quantity
                value = 0
                for s in sorted(list(stock_supplies), key=lambda x: x.date):
                    stock_supply_quantity = s.quantity
                    previously_used = StockSupplySettlement.objects.filter(stock_supply=s)
                    for p in previously_used:
                        stock_supply_quantity -= p.quantity
                    if stock_supply_quantity > quantity_left:
                        StockSupplySettlement.objects.create(
                            settlement=order_settlement, stock_supply=s, quantity=quantity_left
                        )
                        value += s.piece_value() * quantity_left
                        break
                    elif stock_supply_quantity <= quantity_left:
                        StockSupplySettlement.objects.create(
                            settlement=order_settlement, stock_supply=s, quantity=stock_supply_quantity
                        )
                        value += s.piece_value() * stock_supply_quantity
                        s.used = True
                        s.save()
                        quantity_left -= stock_supply_quantity
                return True, value
        return False, 'not enough material'

    def fifo_from_order(self, order, settlement, quantity):
        value_sum = 0
        with transaction.atomic():
            print('ok1')
            delivery_items = DeliveryItem.objects.filter(order=order)
            stock_supplies = []
            used_quantity = 0
            for item in delivery_items:
                print('ok11')
                stock_supply = StockSupply.objects.filter(delivery_item=item, used=False)
                if stock_supply:
                    stock_supplies.extend(list(stock_supply))
            stock_supplies.sort(key=lambda x: x.date)

            for supply in stock_supplies:
                print('ok11', stock_supplies, supply)
                to_use = quantity - used_quantity
                used = 0
                supply_used = StockSupplySettlement.objects.filter(stock_supply=supply, as_result=False)
                for su in supply_used:
                    used += su.quantity
                possible_to_use = supply.quantity - used
                if possible_to_use >= to_use:
                    print('option1')
                    value = money(Decimal(to_use/supply.quantity)*supply.value)
                    value_sum += value
                    print(value, type(value))
                    StockSupplySettlement.objects.create(settlement=settlement, stock_supply=supply, quantity=to_use, value=value)
                    used_quantity += to_use
                    if possible_to_use == to_use:
                        supply.used = True
                        supply.save()
                    break
                else:
                    print('option2')
                    value = money(Decimal(possible_to_use / supply.quantity) * supply.value)
                    value_sum += value
                    print(value, type(value))
                    StockSupplySettlement.objects.create(settlement=settlement, stock_supply=supply, quantity=possible_to_use, value=value)
                    supply.used = True
                    supply.save()
            return value_sum



    def fifo(self):
        stock_supplies = self.get_all_stock_supplies()
        return stock_supplies

    def get_all_stock_supplies(self):
        return StockSupply.objects.filter(name=self.stock.name)

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


class StockSupplySettlement(models.Model):
    stock_supply = models.ForeignKey(StockSupply, on_delete=models.PROTECT)
    settlement = models.ForeignKey(OrderSettlement, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    value = models.DecimalField(max_digits=12, decimal_places=2, editable=False, default=Decimal("0.00"))
    as_result = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.settlement.settlement_date} | {self.stock_supply.name} | {self.quantity} | {self.as_result}'

    def calculate_value(self):
        supply_qty = self.stock_supply.quantity or 0
        if supply_qty == 0:
            return Decimal("0.00")

        supply_value = self.stock_supply.value or Decimal("0.00")

        ratio = Decimal(str(self.quantity)) / Decimal(supply_qty)
        result = ratio * supply_value

        return result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def save(self, *args, **kwargs):
        self.value = self.calculate_value()
        super().save(*args, **kwargs)


class ProductSell3(models.Model):
    customer = models.ForeignKey(Buyer, on_delete=models.PROTECT, null=True, blank=True)
    customer_alter_name = models.CharField(max_length=32, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    warehouse_stock = models.ForeignKey(WarehouseStock, on_delete=models.PROTECT, null=True, blank=True)
    order = models.ForeignKey(Order, on_delete=models.PROTECT, null=True, blank=True)
    quantity = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    date = models.DateField()

    class Meta:
        ordering = ['-date', '-customer', '-product']

    def __str__(self):
        customer = self.customer if self.customer else self.customer_alter_name
        return f'{self.date} | {self.product} {self.quantity} -> {customer}'

    def calculate_value(self):
        return round(self.price * self.quantity, 2)

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
            print('#1')
            return None
        ws = self.warehouse_stock  # zakładamy, że select_related w widoku przyspieszy dostęp
        print(ws.stock.name)
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


class StockSupplySell(models.Model):
    stock_supply = models.ForeignKey(StockSupply, on_delete=models.PROTECT)
    sell = models.ForeignKey(ProductSell3, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()

    class Meta:
        ordering = ['-sell__date']

    def __str__(self):
        return f'[{self.sell.date}] {self.stock_supply.name} -> {self.sell.customer} ({self.quantity})'


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


# class CustomerDelivery(models.Model):
#     customer = models.ForeignKey(Buyer, on_delete=models.PROTECT)
#     date = models.DateField()
#     description = models.CharField(max_length=256, null=True, blank=True)
#     palettes = models.ManyToManyField(Palette, through='DeliveryCustomerPalette', blank=True)
#     items = models.ManyToManyField(ProductSell2, through='DeliverySell', blank=True)
#
#     def __str__(self):
#         return f'{self.customer} {self.date}'
#
#     class Meta:
#         ordering = ['-date']
#
#
# class DeliveryCustomerPalette(models.Model):
#     customer_delivery = models.ForeignKey(CustomerDelivery, on_delete=models.PROTECT)
#     palette = models.ForeignKey(Palette, on_delete=models.PROTECT)
#     quantity = models.IntegerField(default=0)
#
#     def __str__(self):
#         return f'{self.customer_delivery} :: {self.palette} :: {self.quantity}'
#
#
# class DeliverySell(models.Model):
#     customer_delivery = models.ForeignKey(CustomerDelivery, on_delete=models.PROTECT)
#     item = models.ForeignKey(ProductSell2, on_delete=models.PROTECT)
#
#     def __str__(self):
#         return f'{self.customer_delivery} :: {self.item}'


class CustomerPalette(models.Model):
    customer = models.ForeignKey(Buyer, on_delete=models.PROTECT)
    palette = models.ForeignKey(Palette, on_delete=models.PROTECT)
    quantity = models.IntegerField(default=0)

    def __str__(self):
        return f'{self.customer} :: {self.palette} :: {self.quantity}'

    class Meta:
        unique_together = ['customer', 'palette']
        ordering = ['customer']


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

    class Meta:
        ordering = ['-date', '-warehouse_stock']

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


class PriceList(models.Model):
    provider = models.ForeignKey(Provider, on_delete=models.PROTECT)
    date_start = models.DateField()
    date_end = models.DateField(null=True, blank=True)

    def __str__(self):
        if self.date_end:
            return f'{self.provider} :: {self.date_start} - {self.date_end}'
        return f'[ACTIVE]{self.provider} :: {self.date_start}'

    class Meta:
        unique_together = ['provider', 'date_start']


class PriceListItem(models.Model):
    price_list = models.ForeignKey(PriceList, on_delete=models.CASCADE)
    name = models.CharField(max_length=16)
    flute = models.CharField(max_length=4)
    weight = models.IntegerField(default=0)
    etc = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    price = models.IntegerField()
    price2 = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f'{self.name} - {self.price}'

    class Meta:
        unique_together = ['price_list', 'name']


class BOM(models.Model):
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="boms")
    version = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product", "version"],
                name="uniq_bom_product_version",
            ),
        ]

    def __str__(self):
        label = str(self.product)
        return f"{label} v{self.version}"

    def clean(self):
        if self.is_active:
            qs = BOM.objects.filter(product=self.product, is_active=True)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError("Dla danego produktu może być tylko jeden aktywny BOM.")

    @classmethod
    @transaction.atomic
    def create_next_version(cls, *, product, base_bom=None, activate=True):
        last = (
            cls.objects.select_for_update()
            .filter(product=product)
            .order_by("-version")
            .first()
        )
        next_version = 1 if not last else last.version + 1

        if activate:
            cls.objects.filter(product=product, is_active=True).update(is_active=False)

        new_bom = cls.objects.create(
            product=product,
            version=next_version,
            is_active=activate,
        )

        if base_bom:
            parts = base_bom.parts.all()
            cls._copy_parts(parts, new_bom)

        return new_bom

    @staticmethod
    def _copy_parts(parts_qs, new_bom):
        BOMPart.objects.bulk_create(
            [
                BOMPart(bom=new_bom, part=p.part, quantity=p.quantity)
                for p in parts_qs.select_related("part")
            ]
        )

    def requirements(self, order_quantity: int):
        result = []
        for bp in self.parts.select_related("part", "part__stock_type"):
            required = bp.quantity * Decimal(order_quantity)
            result.append((bp.part, required))
        return result

    def to_int_qty(self, stock: "Stock", qty: Decimal) -> int:
        unit = stock.stock_type.unit
        if unit in ("PIECE", "SET"):
            return int(math.ceil(qty))
        raise ValidationError(
            f"Nieobsługiwana jednostka dla realizacji BOM: {unit}. "
            f"Dla KG/M2 potrzebujesz Decimal w stanach magazynowych."
        )


class BOMPart(models.Model):
    bom = models.ForeignKey(
        BOM,
        on_delete=models.CASCADE,
        related_name="parts",
    )
    part = models.ForeignKey(Stock, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=3)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["bom", "part"],
                name="uniq_bompart_bom_part",
            ),
        ]

    def __str__(self):
        return f"{self.part} x {self.quantity}"

