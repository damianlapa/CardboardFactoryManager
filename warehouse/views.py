import datetime
import calendar
from django.shortcuts import render, HttpResponse, redirect
from django.views import View

from django.views.generic import CreateView
from django.urls import reverse_lazy

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import permission_required
from django.utils.decorators import method_decorator
from django.db.models.deletion import ProtectedError

from warehouse.gs_connection import *
from warehouse.models import *
from warehouse.forms import DeliveryItemForm, DeliveryForm, DeliveryPaletteFormSet
from warehousemanager.models import Buyer

from production.models import ProductionOrder, ProductionUnit

import pandas as pd
import pdfplumber

from django.views.generic import ListView

from django.db import transaction
from django.contrib.auth.decorators import user_passes_test


def load_orders(year, row=None, division=None):
    def get_flute(text):
        waves = 0
        for letter in text:
            if letter == '3':
                waves = 3
                break
            elif letter == '5':
                waves = 5
                break
        if waves == 3:
            if 'E' in text.upper():
                return 'E'
            if 'B' in text.upper():
                return 'B'
            if 'C' in text.upper():
                return 'C'
        elif waves == 5:
            if 'EB' in text.upper():
                return 'EB'
            if 'BC' in text.upper():
                return 'BC'
        return None

    year = year if year else datetime.datetime.today().year
    data_all = get_all(year) if year else get_all(str(datetime.datetime.today().year))
    result = ''
    row = row if row else 100
    division = division if division else '10, 15'

    if division:
        start, end = division.split(',')
        rows = [r for r in range(int(start), int(end) + 1)]
    else:
        rows = [row]

    for row in rows:
        try:
            data = data_all[row]

            try:
                customer = Buyer.objects.get(name=data[18].upper().strip())
            except Buyer.DoesNotExist:
                customer = Buyer(name=data[18].upper().strip(), shortcut=data[18].upper().strip()[:5])
                customer.save()

            try:
                provider = Provider.objects.get(shortcut=data[0].upper().strip())
            except Provider.DoesNotExist:
                provider = Provider(name=data[0], shortcut=data[0])
                provider.save()

            try:
                order = Order.objects.get(order_id=f'{data[1].upper().strip()}/{data[2].upper().strip()}',
                                          provider=Provider.objects.get(shortcut=data[0].upper().strip()))
                result += f'{order} already exists<br>'
            except Order.DoesNotExist:
                order = Order(
                    customer=customer,
                    provider=provider,
                    order_id=f'{data[1].upper().strip()}/{data[2].upper().strip()}',
                    customer_date=data[5].upper().strip() if data[5].upper().strip() else data[6].upper().strip(),
                    order_date=data[6].upper().strip() if data[6].upper().strip() else None,
                    order_year=data[5][:4] if data[5] else data[6][:4],
                    delivery_date=data[7].upper().strip() if data[7].upper().strip() else None,
                    production_date=None,
                    dimensions=f'{data[12].upper().strip()}x{data[13].upper().strip()}',
                    name=data[19].upper().strip(),
                    weight=0,
                    order_quantity=data[14].upper().strip(),
                    delivered_quantity=data[15].upper().strip() if data[15].upper().strip() else 0,
                    price=int(float(data[22].upper().strip().replace('\xa0', '').replace(',', '.'))) if data[
                        22] else 0
                )
                order.save()
                result += f'{order} saved<br>'

        except Exception as e:
            result += f'{e}<br>'
    return result


def delete_delivery_ajax(request, delivery_id):
    if request.method == "POST":
        delivery = get_object_or_404(Delivery, id=delivery_id)

        try:
            with transaction.atomic():
                delivery.deliverypalette_set.all().delete()
                delivery.deliveryitem_set.all().delete()
                delivery.delete()
        except ProtectedError:
            return JsonResponse({"success": False,
                                 "message": f"Delivery {delivery.number} can not be deleted. One or more delivery item is already added to stock."})

        return JsonResponse({"success": True, "message": f"Delivery {delivery.number} deleted successfully."})
    return JsonResponse({"success": False, "message": "Invalid request method."})


# to delete? 25-06-24
class TestView(View):
    def get(self, request):
        pass
        # year = request.GET.get('year')
        # data_all = get_all(year) if year else get_all(str(datetime.datetime.today().year))
        # result = ''
        # row = request.GET.get('row')
        # division = request.GET.get('division')
        #
        # result = load_orders(year, row, division)
        #
        # return HttpResponse(result)


class LoadWZ(View):
    def get(self, request):

        return render(request, "warehouse/load_wz.html")

    def post(self, request):
        if "wz_file" not in request.FILES:
            return render(request, "warehouse/load_wz_result.html", {
                "errors": ["No file was uploaded. Please select a file and try again."]
            })
        result = []
        pdf_file = request.FILES["wz_file"]
        errors = []

        with pdfplumber.open(pdf_file) as pdf:
            all_text = ""
            for page in pdf.pages:
                all_text += page.extract_text() + "\n"

        lines = all_text.splitlines()

        provider = ''
        wz_number = ''
        car_number = ''
        date = ''
        phone = ''
        palettes = ''
        orders = []
        p_quantity = ''
        order_num = 1
        number = ''

        cardboard = ''
        dimensions = ''
        quantity = ''
        order_numbers = []

        palletes_list = []

        if 'tfp' in all_text or 'TFP' in all_text:

            for num in range(len(lines)):
                line = lines[num]
                if 'TFP Sp. z o.o.' in line:
                    provider = "TFP"
                if "Data..." in line:
                    date = line.split('.:')[1].strip()
                if "( " in line and " )" in line:
                    phone = line.replace("( ", "").replace(" )", "").strip()
                if "Kopia WZ Nr." in line and not wz_number:
                    wz_number = line.split('.:')[1].strip()
                if "Nr rej./Nazwisko" in line and not car_number:
                    car_number = line.split('.:')[1].split('/')[0].strip()
                if "Powierzone" in line:
                    p_line = line
                    p_line = p_line.split(' ')
                    palettes = f'{p_line[0]};{p_line[1]};{p_line[3].split(",")[0]}'
                    palletes_list.append(palettes)
                if "Nr zam. klienta:" in line:
                    number = line.split("Nr zam. klienta:")[1].split(" ")[0].strip()
                    # try:
                    #     if len(number.split('/')[1]) > 2:
                    #         number = f'{number.split('/')[0]}/{number.split('/')[1][2:4]}'
                    # except Exception as e:
                    #     pass
                    orders.append([number, cardboard, dimensions, quantity])
                if len(line.split(' ')) == 5 or len(line.split(' ')) == 6:
                    line = line.split(' ')
                    if line[0][0].isdigit() and line[1][-1] == '\xad' and 'x' in line[2]:
                        cardboard = line[1][:-1]
                        dimensions = line[2]
                        quantity = line[3].split(',')[0] if len(line) == 5 else f'{line[3]}{line[4]}'.split(',')[0]

                if "Ilość na palecie: " in line:
                    if order_num == len(orders):
                        p_quantity += f'{line.split("palecie:")[1].split(",")[0].strip().replace(" ", "")};'
                    else:
                        orders[-2].append(p_quantity)
                        order_num += 1
                        p_quantity = f'{line.split("palecie:")[1].split(",")[0].strip().replace(" ", "")};'

            orders[-1].append(p_quantity)

            date = date.replace('­', '.').split('.')
            if int(date[0]) > 31:
                date = (date[2], date[1], date[0])

        else:
            for num in range(len(lines)):
                line = lines[num]
                if 'JASSBOARD SP. Z O.O.' in line:
                    provider = "JASS"
                if "Data wystawienia: " in line:
                    date = line.split('wystawienia: ')[1].strip().replace('-', '.').split('.')
                    date = date[2], date[1], date[0]
                if "Nr rejestracyjny: " in line:
                    try:
                        phone, car_number = line.split("Nr rejestracyjny: ")[1].split(' ')
                    except ValueError:
                        car_number = 'None'
                        phone = 'None'
                if "Numer WZ" in line and not wz_number:
                    wz_number = lines[num + 1].strip()
                if "PALETA" in line:
                    p_line = line.split(' ')
                    palette = p_line[0].split('_')
                    palette_type = 'Paleta'
                    if palette[1] == 'EURO':
                        palette_type = 'EPAL'
                    palette_dimensions = palette[2].lower().split('x')
                    palette_dimensions = f'{palette_dimensions[1]}x{palette_dimensions[0]}'
                    palettes = f'{palette_type};{palette_dimensions};{p_line[1]}'
                    palletes_list.append(palettes)
                if "nr zam.:" in line.lower():
                    number = line.lower().split("nr zam.:")[1].replace('jass', '').strip()
                    if number not in order_numbers:
                        order_numbers.append(number)
                if "ark" in line and 'm2' in line and not "RAZEM" in line and not 'Ilość wysłana' in line:
                    cardboard_line = line.split(' ')
                    cardboard = cardboard_line[1][:-9] if cardboard_line[1][2].isdigit() else cardboard_line[1][:-8]
                    dimensions = cardboard_line[1][-9:] if cardboard_line[1][2].isdigit() else cardboard_line[1][-8:]
                    p_quantity += f'{cardboard_line[3]};' if len(cardboard_line) == 7 else f'{cardboard_line[3]}{cardboard_line[4]};'
                    p_quantity.replace(',', '')
                if cardboard in line and "RAZEM" in line:
                    quantity_line = line.split(" ")
                    quantity = quantity_line[3].replace(',', '')
                    if len(dimensions) == 9:
                        dimensions_data = dimensions.split('*')
                    else:
                        dimensions_data = dimensions[:-4], dimensions[4:]
                    dimensions = f'{str(int(dimensions_data[1]))}x{str(int(dimensions_data[0]))}'
                    orders.append([number, cardboard, dimensions, quantity, p_quantity])
                    p_quantity = ''

        try:
            delivery, created = Delivery.objects.get_or_create(
                number=wz_number,
                defaults={
                    'provider': Provider.objects.get(shortcut=provider),
                    'date': datetime.date(int(date[2]), int(date[1]), int(date[0])),
                    'car_number': car_number[:16],
                    'telephone': phone.replace(' ', ''),
                }
            )
            if not created:
                errors.append(f'Delivery with number {wz_number} already exists.<br>')
                return render(request, "warehouse/load_wz_result.html", {
                    "errors": errors
                })

            for p in palletes_list:
                palettes = p

                try:
                    palette = Palette.objects.get(name=f'{palettes.split(";")[0]} {palettes.split(";")[1]}')
                except Palette.DoesNotExist:
                    palette = Palette.objects.create(name=f'{palettes.split(";")[0]} {palettes.split(";")[1]}')
                    palette.save()

                delivery_palette = DeliveryPalette.objects.create(
                    delivery=delivery,
                    palette=palette,
                    quantity=int(palettes.split(';')[2])
                )
                delivery_palette.save()

        except Provider.DoesNotExist:
            errors.append(f'Provider {provider} does not exist.')
        except Exception as e:
            errors.append(f'Error creating delivery: {str(e)}')

        for order in orders:
            print(order)
            try:
                p_quantity_counted = 0
                for p in order[4].split(';'):
                    if p:
                        p_quantity_counted += int(p)
                if p_quantity_counted != int(order[3]):
                    order[3] = p_quantity_counted
                    result.append(f'Order {order[0]}: Quantity corrected to {p_quantity_counted}')
            except Exception as e:
                errors.append(f'Error with order {order[0]}: {str(e)}')
            try:
                Order.objects.get(provider=delivery.provider, order_id=order[0])
            except Order.DoesNotExist:
                load_orders(year=None, row=None, division='5, 3000')
            try:
                if '/' in order[0] and len(order[0].split('/')[1]) > 2:
                    order_split = order[0].split('/')
                    order[0] = str(order_split[0]) + '/' + str(order_split[1][2:4])
                delivery_item = DeliveryItem.objects.create(
                    delivery=delivery,
                    order=Order.objects.get(provider=delivery.provider, order_id=order[0]),
                    quantity=order[3],
                    palettes_quantity=order[4]
                )
                delivery_item.save()
                result.append(f'Order {order[0]} successfully linked to delivery.')
            except Order.DoesNotExist:
                errors.append(f'Order {order[0]} does not exist for provider {delivery.provider}.')
            except Exception as e:
                errors.append(f'Error with delivery item for order {order[0]}: {str(e)}')

        return render(request, "warehouse/load_wz_result.html", {"results": result, "errors": errors})


class OrderListView(View):
    def get(self, request):
        sort_by = request.GET.get('sort', 'order_date')
        order_direction = request.GET.get('dir', 'asc')
        manual = request.GET.get('manual')
        all_orders = request.GET.get('all')

        if order_direction == 'desc':
            sort_by = f'-{sort_by}'
        if all_orders:
            orders = Order.objects.all().order_by(sort_by)
        else:
            orders = Order.objects.filter(delivered=True).order_by(sort_by)
        if manual:
            year = request.GET.get('year')
            orders = Order.objects.filter(provider=Provider.objects.get(name=manual))
            orders_ = []
            for o in orders:
                try:
                    number, year_str = o.order_id.split('/')
                    number = int(number)
                    if year and year == year_str:
                        orders_.append((number, o))
                except:
                    pass
            orders_ = sorted(orders_, key=lambda x: x[0])

            orders = [o[1] for o in orders_]

        return render(request, 'warehouse/order_list.html', locals())


class OrderDetailView(View):
    def get(self, request, order_id):
        stock_types = StockType.objects.all()
        order = Order.objects.get(id=order_id)
        warehouses = Warehouse.objects.all()
        settlements = OrderSettlement.objects.filter(order=order)
        warehouse_stocks_history = WarehouseStockHistory.objects.filter(order_settlement__in=settlements)

        products = [order.product]
        warehouse_products = None
        for p in products:
            stock_type = models.ForeignKey(StockType, on_delete=models.PROTECT)
            delivery_item = models.ForeignKey(DeliveryItem, on_delete=models.PROTECT, null=True, blank=True)
            dimensions = models.CharField(max_length=32, null=True, blank=True)
            date = models.DateField(null=True, blank=True)
            quantity = models.PositiveIntegerField(default=0)
            name = models.CharField(max_length=64)
            try:
                warehouse_product_stock = Stock.objects.get(name=name)
                warehouse_products.append(warehouse_product_stock)
            except Stock.DoesNotExist:
                pass
        items = DeliveryItem.objects.filter(order=order)
        stock_supplies = StockSupply.objects.filter(delivery_item__in=items)
        stock_materials = []
        all_materials_in_warehouse = WarehouseStock.objects.filter(warehouse=Warehouse.objects.get(name="MAGAZYN GŁÓWNY"))
        for stock_supply in stock_supplies:
            try:
                stock = Stock.objects.get(name=stock_supply.name)
                warehouse_stock = WarehouseStock.objects.get(stock=stock)
                stock_materials.append(warehouse_stock)

            except Exception as e:
                pass
        stocks = StockSupply.objects.all()

        try:
            production_order = ProductionOrder.objects.get(id_number=f'{order.provider} {order.order_id}')
            production_units = ProductionUnit.objects.filter(production_order=production_order).order_by('sequence')
            cost = order.production_cost()
            other = order.other_costs()
            total_expenses = round(sum((order.material_cost(), sum(cost), sum(other))), 2)
            earnings = order.total_sales()
            result = earnings - total_expenses
            if production_units:
                last_unit = list(production_units)[-1]
                lq = last_unit.quantity_end
                ld = last_unit.end.date()
        except ProductionOrder.DoesNotExist:
            production_units = []
        return render(request, 'warehouse/order_details.html', locals())


class DeliveriesView(View):
    def get(self, request):
        deliveries = Delivery.objects.all().prefetch_related('deliverypalette_set__palette')
        return render(request, 'warehouse/delivery_list.html', locals())


class DeliveryDetailView(View):
    def get(self, request, delivery_id):
        delivery = Delivery.objects.get(id=delivery_id)
        items = DeliveryItem.objects.filter(delivery=delivery)
        form = DeliveryItemForm(initial={'delivery': delivery})
        return render(request, 'warehouse/delivery_details.html', locals())


class DeliveryEditView(View):
    def get(self, request, delivery_id):
        delivery = Delivery.objects.get(id=delivery_id)
        form = DeliveryForm(instance=delivery)
        palette_formset = DeliveryPaletteFormSet(instance=delivery)
        context = {'delivery': delivery, "form": form, "palette_formset": palette_formset}

        return render(request, "warehouse/delivery-edit.html", context=context)

    def post(self, request, delivery_id):
        delivery = Delivery.objects.get(id=delivery_id)
        form = DeliveryForm(request.POST, instance=delivery)
        palette_formset = DeliveryPaletteFormSet(request.POST, instance=delivery)

        if form.is_valid() and palette_formset.is_valid():
            form.save()
            palette_formset.save()
            return redirect('warehouse:delivery-detail-view', delivery_id=delivery_id)

        context = {
            'delivery': delivery,
            'form': form,
            'palette_formset': palette_formset,
        }
        return render(request, "warehouse/delivery-edit.html", context)


class AddDeliveryItem(View):
    def post(self, request):
        form = DeliveryItemForm(request.POST)
        delivery_id = form.data['delivery']
        if form.is_valid():
            form.save()
            return redirect('warehouse:delivery-detail-view', delivery_id=delivery_id)


class AddDeliveryToWarehouse(View):
    def post(self, request, delivery_id):
        delivery = Delivery.objects.get(id=delivery_id)
        items = DeliveryItem.objects.filter(delivery=delivery)
        delivery.add_to_warehouse()

        return redirect("warehouse:delivery-detail-view", delivery_id=delivery_id)


class WarehouseView(View):
    def get(self, request, warehouse_id):
        warehouse = Warehouse.objects.get(id=warehouse_id)
        stocks = WarehouseStock.objects.filter(warehouse=warehouse, quantity__gt=0)
        return render(request, 'warehouse/warehouse_details.html', locals())


class WarehouseListView(View):
    def get(self, request):
        warehouses = Warehouse.objects.all()
        return render(request, 'warehouse/warehouse_list.html', locals())


class DeliveriesStatistics(View):
    def get(self, request):
        start = request.GET.get('start')
        if start:
            d, m, y = list(map(int, start.split('-')))
            start = datetime.date(y, m, d)
        else:
            start = datetime.date(2025, 1, 1)
        dates = [start]
        weeks = ['#0']
        values = [0]
        values_by_week = [0]

        end = start + datetime.timedelta(days=7-start.isoweekday())

        while start <= datetime.date.today():

            deliveries = Delivery.objects.all().filter(date__gte=start, date__lte=end)
            total = 0
            for d in deliveries:
                total += int(d.count_area())
            dates.append(end)
            values.append(values[-1] + total)
            weeks.append(f'#{len(weeks)}')
            values_by_week.append(total)

            start = end + datetime.timedelta(days=1)
            end = end + datetime.timedelta(days=7)

        total_amount = sum(values_by_week)
        cel = 2000000
        ile = cel - total_amount
        year_days = 365 + calendar.isleap(datetime.datetime.now().year)
        days_left = year_days - datetime.datetime.now().timetuple().tm_yday

        from collections import defaultdict

        orders_by_customer = defaultdict(int)
        orders_by_provider = defaultdict(int)

        for d in Delivery.objects.all():
            provider = d.provider.name
            area = d.count_area()
            orders_by_provider[provider] += int(round(area, 0))
            for item in DeliveryItem.objects.filter(delivery=d):
                try:
                    customer = item.order.customer.name  # Zakładam strukturę relacji
                    orders_by_customer[customer] += int(round(item.calculate_area(), 0))
                except AttributeError:
                    continue  # Pomijamy błędne wpisy

        # Zamieniamy na listy do wykresu
        customer_labels = []
        customer_values = []

        customer_results = []
        for key in orders_by_customer.keys():
            customer_results.append((key, orders_by_customer[key]))

        customer_results = sorted(customer_results, key=lambda x: x[0])

        for c in customer_results:
            customer_, result = c
            customer_labels.append(customer_)
            customer_values.append(result)

        provider_labels = list(orders_by_provider.keys())
        provider_values = list(orders_by_provider.values())

        return render(request, 'warehouse/deliveries-statistics.html', locals())


class StockView(View):
    def get(self, request, stock_id):
        stock = Stock.objects.get(id=stock_id)
        # deliveries_items = DeliveryItem.objects.

        return render(request, 'warehouse/stock-details.html', locals())


class LoadDeliveryToGSFile(View):
    def get(self, request, delivery_id):

        delivery = Delivery.objects.get(id=delivery_id)
        items = DeliveryItem.objects.filter(delivery=delivery)
        numbers = []
        values = []
        for item in items:
            order_id = item.order.order_id
            number, year = map(int, order_id.split('/'))
            numbers.append(number)
            values.append(item.quantity)

        get_rows_numbers(numbers, 2025, delivery.provider, values)

        delivery.updated = True
        delivery.save()

        return redirect("warehouse:delivery-detail-view", delivery_id=delivery_id)


class SellProductList(View):
    def get(self, request):
        sells = ProductSell.objects.select_related('warehouse_stock', 'customer').order_by('-date')
        warehouse_stocks = WarehouseStock.objects.filter(quantity__gte=0, warehouse=Warehouse.objects.get(name="MAGAZYN WYROBÓW GOTOWYCH"))
        context = {
            "warehouse_stocks": warehouse_stocks,
            "customers": Buyer.objects.all(),
            "sells": sells
        }
        return render(request, "warehouse/sell-product-list.html", context=context)


class ProductSellCreateView(CreateView):
    model = ProductSell
    fields = ['warehouse_stock', 'quantity', 'customer', 'price', 'date']
    success_url = reverse_lazy('warehouse:sells-list-view')

    def form_valid(self, form):
        with transaction.atomic():
            date = form.cleaned_data['date']
            self.object = form.save()

            stock = self.object.warehouse_stock

            warehouse_stock_history = WarehouseStockHistory.objects.create(
                warehouse_stock=stock,
                quantity_before=stock.quantity,
                quantity_after=stock.quantity - self.object.quantity,
                date=date
            )

            stock.quantity -= self.object.quantity
            if stock.quantity < 0:
                form.add_error('quantity', 'Nie ma wystarczającej ilości w magazynie!')
                raise transaction.TransactionManagementError("Za mało towaru")
            stock.save()

        return super().form_valid(form)


