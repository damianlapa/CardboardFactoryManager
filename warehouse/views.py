# warehouse/views.py

from django.shortcuts import HttpResponse
from django.views import View
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.db.models.deletion import ProtectedError
from django.views.generic import CreateView
from django.urls import reverse
from django.contrib import messages
from django.shortcuts import redirect
from warehouse.gs_connection import *
from warehouse.models import *
from warehouse.forms import DeliveryItemForm, DeliveryForm, DeliveryPaletteFormSet, DeliverySpecialItemForm, \
    OrderToOrderShiftForm, ManuallyOrdersForm
from warehousemanager.models import Buyer, LocalSetting
from production.models import ProductionOrder, ProductionUnit
import pdfplumber
from django.db import transaction
from django.db.models import Sum
import datetime, calendar
from collections import defaultdict
from django.shortcuts import render
from django.utils.timezone import now
from django.db.models import Prefetch
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from warehouse.services.bom_preview import bom_preview_for_order
from warehouse.services.bom_realization import realize_order_bom


def load_orders(year, row=None, division=None, row_list=None):
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
    row = row if row else None
    division = division if division else None

    if division:
        start, end = division.split(',')
        rows = [r for r in range(int(start), int(end) + 1)]
    elif row:
        rows = [row]
    else:
        rows = []

    if row_list:
        rows = row_list
    for row in rows:
        try:
            data = data_all[row]
            print(data, '#2')
            try:
                print('customer jest')
                customer = Buyer.objects.get(name=data[18].upper().strip())
            except Buyer.DoesNotExist:
                print('customer jest nie ')
                customer = Buyer(name=data[18].upper().strip(), shortcut=data[18].upper().strip()[:5])
                customer.save()

            try:
                print('dostawca jest')
                provider = Provider.objects.get(shortcut=data[0].upper().strip())
            except Provider.DoesNotExist:
                print('dostawca jest nie')
                provider = Provider(name=data[0], shortcut=data[0])
                provider.save()

            flute = get_flute(data[19].upper().strip())
            dimensions = f'{data[12].strip()}x{data[13].strip()}'
            product_additional_name = data[24].upper().strip()

            product_name = f'{customer.name} | {flute} | {data[23].lower().strip()} | {product_additional_name}'

            print(product_name, dimensions, flute)

            # Pobierz lub utwórz produkt
            try:
                print('produkt jest')
                product = Product.objects.get(name=product_name)
            except Product.DoesNotExist:
                print('produkt jest nie')
                if all((product_name, dimensions, flute)):
                    product = Product.objects.create(
                        name=product_name,
                        dimensions=dimensions,
                        flute=flute,
                        gsm=0  # lub odczytaj z danych, jeśli dostępne
                    )

            try:
                print('order jest')
                order = Order.objects.get(order_id=f'{data[1].upper().strip()}/{data[2].upper().strip()}',
                                          provider=Provider.objects.get(shortcut=data[0].upper().strip()))
                result += f'{order} already exists<br>\n'

            except Order.DoesNotExist:
                print('order jest nie')
                price = int(float(data[22].upper().strip().replace('\xa0', '').replace(',', '.'))) if data[
                    22] else 0
                order_date = data[6].upper().strip() if data[6].upper().strip() else None
                order = Order(
                    customer=customer,
                    provider=provider,
                    order_id=f'{data[1].upper().strip()}/{data[2].upper().strip()}',
                    customer_date=data[5].upper().strip() if data[5].upper().strip() else data[6].upper().strip(),
                    order_date=order_date,
                    order_year=data[5][:4] if data[5] else data[6][:4],
                    delivery_date=None,
                    production_date=None,
                    dimensions=f'{data[12].upper().strip()}x{data[13].upper().strip()}',
                    name=data[19].upper().strip(),
                    weight=0,
                    order_quantity=data[14].upper().strip(),
                    delivered_quantity=data[15].upper().strip() if data[15].upper().strip() else 0,
                    price=price,
                    product=product
                )
                if price and order_date:
                    order.save()
                    result += f'{order} saved<br>'
                elif provider.name == "PAKER":
                    order.price = 0
                    order.save()
                else:
                    print(provider, type(provider))
                    result += f'{data[1].upper().strip()}/{data[2].upper().strip()} no cardboard price or order date\n'

        except Exception as e:
            result += f'{e}<br>\n'

    print(result)
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


class LoadWZ(LoginRequiredMixin, View):
    login_url = reverse_lazy('login')

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

        order_data = []

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

        elif 'AQUILA' in all_text or 'aquila' in all_text:

            for num in range(len(lines)):
                line = lines[num]

                if not provider:
                    if 'aquila' in line.lower():
                        provider = 'AQ'

                if not wz_number:
                    if "PAKER SPÓŁKA Z OGRANICZONĄ" in line:
                        s_line = line.split(' ')
                        wz_number = s_line[-2]
                        date = s_line[-1].split('/')

                if not phone:
                    if "Nr tel./rejestracyjny" in line:
                        phone = line.split(' ')[-1]

                if "Tektura falista Jakość " in line:
                    if order_data:
                        orders.append(order_data)
                        order_data = []
                    line = line.replace('Tektura falista Jakość ', '')
                    line = line.split(' ')
                    cardboard = line[0]
                    dimensions = ''.join((line[1], line[2], line[3]))
                    quantity = line[6]

                    order_data.extend((None, cardboard, dimensions, quantity, None))

                if "Bigi" in line:
                    order_num_line = lines[num + 1]
                    order_num = order_num_line.split(' ')[1]
                    if order_data:
                        order_data[0] = order_num

                if "STOS" in line:
                    line = line.split(' ')
                    if order_data:
                        if not order_data[4]:
                            order_data[4] = f'{line[0]}x{line[3].replace(".", "")}'
                        else:
                            order_data[4] += f';{line[0]}x{line[3].replace(".", "")}'

                if "Paleta" in line:
                    palletes_item = ''
                    if "Euro" in line:
                        palletes_item += 'EPAL;'
                    else:
                        palletes_item += 'Paleta;'
                    line = line.replace('..', '')
                    line = line.strip().split(' ')
                    palletes_item += f'{line[-3]}x{line[-5]};{line[-1]}'
                    palletes_list.append(palletes_item)

            orders.append(order_data)

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
                    p_quantity += f'{cardboard_line[3]};' if len(
                        cardboard_line) == 7 else f'{cardboard_line[3]}{cardboard_line[4]};'
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
        wrong_orders = []
        numbers = []
        year_orders = {} # new
        for o in orders:
            try:
                order_num_split, year_num_split = o[0].split('/')
                if len(year_num_split) == 2:
                    year_num_split = '20' + year_num_split
                if year_num_split in year_orders.keys():
                    year_orders[year_num_split].append(int(order_num_split))
                else:
                    year_orders[year_num_split] = [int(order_num_split)]
            except ValueError:
                errors.append(f'Error creating item: {o}')
                wrong_orders.append(o)

        for key in year_orders:
            nums = get_rows_numbers2(year_orders[key], int(key), delivery.provider)
            load_orders(key, row_list=nums)

            for wrong_order in wrong_orders:
                orders.remove(wrong_order)

        for order in orders:
            try:
                p_quantity_counted = 0
                for p in order[4].split(';'):
                    if p:
                        if 'x' in p:
                            p = p.split('x')
                            p = int(p[0]) * int(p[1])
                        p_quantity_counted += int(p)
                if p_quantity_counted != int(order[3]):
                    order[3] = p_quantity_counted
                    result.append(f'Order {order[0]}: Quantity corrected to {p_quantity_counted}')
            except Exception as e:
                errors.append(f'Error with order {order[0]}: {str(e)}')
            try:
                order_id_num, order_id_year = order[0].split('/')
                if len(order_id_year) > 2:
                    temp_order_id_year = ''
                    for char in order_id_year:
                        if str(char).isdigit() and str(char) in '0123456789':
                            print(char)
                            temp_order_id_year += str(char)
                    order_id_year = temp_order_id_year
                    if len(order_id_year) > 2:
                        order_id_year = str(int(order_id_year) - 2000)
                    print(order_id_year)
                    Order.objects.get(provider=delivery.provider, order_id=f'{order_id_num}/{order_id_year}')
                else:
                    Order.objects.get(provider=delivery.provider, order_id=order[0])
            except Order.DoesNotExist:
                print('none')
                pass
            try:
                if '/' in order[0] and len(order[0].split('/')[1]) > 2:
                    order_split = order[0].split('/')
                    temp = ''
                    for char in order_split[1]:
                        if str(char).isdigit() and str(char) in '0123456789':
                            temp += str(char)
                    if len(temp) > 2:
                        order[0] = str(order_split[0]) + '/' + temp[2:4]
                    else:
                        order[0] = str(order_split[0]) + '/' + temp
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

        return render(request, "warehouse/load_wz_result.html",
                      {"results": result, "errors": errors, "delivery": delivery})


class OrderListView(LoginRequiredMixin, View):
    login_url = reverse_lazy('login')

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
            orders = Order.objects.filter(delivered=True, finished=False).order_by(sort_by)
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

        orders_num = len(list(orders))
        return render(request, 'warehouse/order_list.html', locals())


class OrderDetailView(LoginRequiredMixin, View):
    login_url = reverse_lazy('login')

    def post(self, request, order_id):
        order = Order.objects.get(id=order_id)
        action = request.POST.get("action")

        if action == "bom_preview":
            try:
                data = bom_preview_for_order(order)
                return JsonResponse({"ok": True, "data": data})
            except ValidationError as e:
                return JsonResponse({"ok": False, "error": str(e)}, status=400)
            except Exception as e:
                return JsonResponse({"ok": False, "error": f"{e}"}, status=500)

        if action == "bom_execute":
            try:
                preview = bom_preview_for_order(order)
                if not preview["ok"]:
                    return JsonResponse({"ok": False, "error": "Braki materiałowe – rozchód zablokowany."}, status=400)

                realize_order_bom(order=order)
                return JsonResponse({"ok": True})
            except ValidationError as e:
                return JsonResponse({"ok": False, "error": str(e)}, status=400)
            except Exception as e:
                return JsonResponse({"ok": False, "error": f"{e}"}, status=500)

        return JsonResponse({"ok": False, "error": "Nieznana akcja."}, status=400)

    def get(self, request, order_id):
        stock_types = StockType.objects.all()
        order = Order.objects.get(id=order_id)
        warehouses = Warehouse.objects.all()
        settlements = OrderSettlement.objects.filter(order=order)
        warehouse_stocks_history = WarehouseStockHistory.objects.filter(order_settlement__in=settlements)
        sales = ProductSell3.objects.filter(order=order)

        # attempt
        shifts_to = OrderToOrderShift.objects.filter(order_to=order)
        shifts_from = OrderToOrderShift.objects.filter(order_from=order)
        shifts = shifts_to
        products = [order.product]

        warehouse_products = None
        for p in products:
            stock_type = models.ForeignKey(StockType, on_delete=models.PROTECT)
            delivery_item = models.ForeignKey(DeliveryItem, on_delete=models.PROTECT, null=True, blank=True)
            dimensions = models.CharField(max_length=32, null=True, blank=True)
            date = models.DateField(null=True, blank=True)
            quantity = models.PositiveIntegerField(default=0)
            name = models.CharField(max_length=64)
            price = p.price
            try:
                warehouse_product_stock = Stock.objects.get(name=name)
                warehouse_products.append(warehouse_product_stock)
            except Stock.DoesNotExist:
                pass

        # attempt
        items = DeliveryItem.objects.filter(order=order)
        items = list(items)

        # price list
        # price_list_date = order.order_date
        # price_list_provider = order.provider
        # price_item_name = order.name
        #
        # price_list = PriceList.objects.filter(
        #     provider=price_list_provider,
        #     # date_start__lte=price_list_date,
        #     # date_end__gte=price_list_date
        # )
        # print(price_list)
        # if price_list:
        #     price_item = PriceListItem.objects.filter(price_list=price_list[0], name=price_item_name)[0]
        #     print(price_item)

        # for s in shifts_to:
        #     print(s.get_value())
        #     s_items = DeliveryItem.objects.filter(order=s.order_from)
        #     if s_items:
        #         items.append(s_items[0])

        stock_supplies = StockSupply.objects.filter(delivery_item__in=items)
        stock_materials = []
        all_materials_in_warehouse = WarehouseStock.objects.filter(
            warehouse=Warehouse.objects.get(name="MAGAZYN GŁÓWNY"))
        for stock_supply in stock_supplies:
            try:
                stock = Stock.objects.get(name=stock_supply.name)
                warehouse_stock = WarehouseStock.objects.get(stock=stock)
                if warehouse_stock not in stock_materials:
                    stock_materials.append(warehouse_stock)

            except Exception as e:
                pass

        if shifts_to:
            stock_materials = shifts_to[0].get_items()
            shift_quantity = 0
            for s in shifts_to:
                shift_quantity += s.quantity

        stocks = StockSupply.objects.all()

        ld = None

        try:
            production_order = ProductionOrder.objects.get(id_number=f'{order.provider} {order.order_id}')
            production_units = ProductionUnit.objects.filter(production_order=production_order).order_by('sequence')
            cost = order.production_cost()
            other = order.other_costs()
            total_expenses = round(sum((order.material_cost(), sum(cost), sum(other))), 2)
            earnings = order.total_sales()
            result = round(earnings - total_expenses, 2)
            if production_units:
                last_unit = list(production_units)[-1]
                lq = last_unit.quantity_end
                ld = last_unit.end.date()
        except ProductionOrder.DoesNotExist:
            cost = order.production_cost()
            other = order.other_costs()
            total_expenses = round(sum((order.material_cost(), sum(cost), sum(other))), 2)
            earnings = order.total_sales()
            result = round(earnings - total_expenses, 2)
            production_units = []

        # product sell 3
        products_sell = Product.objects.all()
        default_product = order.product

        customers_sell = Buyer.objects.all()
        default_customer = order.customer

        warehouse_stocks_sell = WarehouseStock.objects.all()
        if settlements:
            history = WarehouseStockHistory.objects.filter(order_settlement__in=settlements)

            for h in history:
                if h.warehouse_stock.warehouse.name == 'MAGAZYN WYROBÓW GOTOWYCH':
                    default_warehouse_stock = h.warehouse_stock
                    quantity = h.warehouse_stock.quantity

        today = datetime.date.today().isoformat()

        if not ld:
            if items:
                for i in items:
                    if ld:
                        if ld < i.delivery.date:
                            ld = i.delivery.date
                    else:
                        ld = i.delivery.date

        # w OrderDetailView.get(...)
        orders_other = Order.objects.exclude(id=order.id).order_by("-id")  # [:100]  # do selecta w modalu

        return render(request, 'warehouse/order_details.html', locals())


class AddShiftView(LoginRequiredMixin, View):
    login_url = reverse_lazy('login')

    def post(self, request, order_id):
        order_from = get_object_or_404(Order, id=order_id)
        form = OrderToOrderShiftForm(request.POST)

        if form.is_valid():
            shift: OrderToOrderShift = form.save(commit=False)
            shift.order_from = order_from
            # jeśli masz logikę wyliczania wartości, możesz tu ją uzupełnić
            # shift.value = shift.quantity * (shift.order_to.product.price or 0)
            shift.save()
            messages.success(request, "Shift added.")
            return redirect(request.META.get('HTTP_REFERER', '/'))
        else:
            messages.error(request, f"Cannot add shift: {form.errors.as_text()}")

        return redirect(request.META.get('HTTP_REFERER', '/'))


class DeliveriesView(LoginRequiredMixin, View):
    login_url = reverse_lazy('login')

    PAGE_SIZE = 30

    def get_queryset(self, request):
        special = request.GET.get("special")
        provider = request.GET.get("provider")

        if special:
            return DeliverySpecial.objects.all().order_by("-date")

        qs = Delivery.objects.all().prefetch_related(
            'deliverypalette_set__palette'
        ).order_by("-date", "-number")

        if provider:
            qs = qs.filter(provider__shortcut=provider)

        return qs

    def get(self, request):
        special = request.GET.get("special")
        provider = request.GET.get("provider")

        deliveries_qs = self.get_queryset(request)

        paginator = Paginator(deliveries_qs, self.PAGE_SIZE)
        page_obj = paginator.get_page(request.GET.get("page", 1))

        deliveries = page_obj.object_list
        is_paginated = page_obj.paginator.num_pages > 1

        is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"
        if is_ajax:
            html = render_to_string(
                "warehouse/_delivery_rows.html",
                {"deliveries": deliveries},
                request=request
            )
            return JsonResponse({"html": html, "has_next": page_obj.has_next()})

        return render(request, "warehouse/delivery_list.html", {
            "deliveries": deliveries,
            "page_obj": page_obj,
            "is_paginated": is_paginated,
            "special": special,
            "provider": provider,
        })


class DeliveryDetailView(LoginRequiredMixin, View):
    login_url = reverse_lazy('login')

    def get(self, request, delivery_id):
        delivery = Delivery.objects.get(id=delivery_id)
        items = DeliveryItem.objects.filter(delivery=delivery).order_by('id')
        form = DeliveryItemForm(initial={'delivery': delivery})
        return render(request, 'warehouse/delivery_details.html', locals())


class DeliverySpecialDetailView(LoginRequiredMixin, View):
    login_url = reverse_lazy('login')

    def get(self, request, delivery_id):
        delivery = DeliverySpecial.objects.get(id=delivery_id)
        items = DeliverySpecialItem.objects.filter(delivery=delivery)
        form = DeliverySpecialItemForm(initial={'delivery': delivery})
        return render(request, 'warehouse/delivery_special_details.html', locals())


class DeliveryEditView(LoginRequiredMixin, View):
    login_url = reverse_lazy('login')

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


class AddDeliveryItem(LoginRequiredMixin, View):
    login_url = reverse_lazy('login')

    def post(self, request):
        form = DeliveryItemForm(request.POST)
        delivery_id = form.data['delivery']
        if form.is_valid():
            form.save()
            return redirect('warehouse:delivery-detail-view', delivery_id=delivery_id)


class AddDeliverySpecialItem(LoginRequiredMixin, View):
    login_url = reverse_lazy('login')

    def post(self, request):
        form = DeliverySpecialItemForm(request.POST)
        delivery_id = form.data['delivery']
        if form.is_valid():
            form.save()
            return redirect('warehouse:delivery-special-detail-view', delivery_id=delivery_id)
        else:
            errors = form.errors
            r = ''
            for e in errors:
                r += f'{e}<br>'
            return HttpResponse(r)


class AddDeliveryItemToWarehouse(LoginRequiredMixin, View):
    login_url = reverse_lazy('login')

    def get(self, request, delivery_id, item_id):
        item = DeliveryItem.objects.get(id=item_id)
        item.add_to_warehouse()

        return redirect("warehouse:delivery-detail-view", delivery_id=delivery_id)


class AddDeliveryToWarehouse(LoginRequiredMixin, View):
    login_url = reverse_lazy('login')

    def post(self, request, delivery_id):
        delivery = Delivery.objects.get(id=delivery_id)
        items = DeliveryItem.objects.filter(delivery=delivery)
        delivery.add_to_warehouse()

        return redirect("warehouse:delivery-detail-view", delivery_id=delivery_id)


class AddDeliverySpecialToWarehouse(LoginRequiredMixin, View):
    login_url = reverse_lazy('login')

    def post(self, request, delivery_id):
        delivery = DeliverySpecial.objects.get(id=delivery_id)
        items = DeliverySpecialItem.objects.filter(delivery=delivery)
        delivery.add_to_warehouse()

        return redirect("warehouse:delivery-special-detail-view", delivery_id=delivery_id)


class AddDeliverySpecialItemToWarehouse(LoginRequiredMixin, View):
    login_url = reverse_lazy('login')

    def get(self, request, delivery_id, item_id):
        item = DeliverySpecialItem.objects.get(id=item_id)
        item.add_to_warehouse()

        return redirect("warehouse:delivery-special-detail-view", delivery_id=delivery_id)


class WarehouseView(LoginRequiredMixin, View):
    login_url = reverse_lazy('login')

    def get(self, request, warehouse_id):
        all_stocks = request.GET.get('all_stocks')
        warehouse = Warehouse.objects.get(id=warehouse_id)
        if not all_stocks:
            stocks = WarehouseStock.objects.filter(warehouse=warehouse, quantity__gt=0)
        else:
            stocks = WarehouseStock.objects.filter(warehouse=warehouse)
        return render(request, 'warehouse/warehouse_details.html', locals())


class WarehouseListView(LoginRequiredMixin, View):
    login_url = reverse_lazy('login')

    def get(self, request):
        warehouses = Warehouse.objects.all()
        return render(request, 'warehouse/warehouse_list.html', locals())


class DeliveriesStatistics(LoginRequiredMixin, View):
    login_url = reverse_lazy('login')
    template_name = 'warehouse/deliveries-statistics.html'

    def _parse_date(self, s, default):
        if not s:
            return default
        try:
            d, m, y = map(int, s.split('-'))  # 'dd-mm-yyyy'
            return datetime.date(y, m, d)
        except Exception:
            return default

    def _week_start(self, d: datetime.date) -> datetime.date:
        # poniedziałek wg ISO (1=Mon)
        return d - datetime.timedelta(days=d.isoweekday() - 1)

    def _month_start(self, d: datetime.date) -> datetime.date:
        return d.replace(day=1)

    def _period_key_end(self, key: datetime.date, group: str) -> datetime.date:
        if group == 'month':
            last_day = calendar.monthrange(key.year, key.month)[1]
            return key.replace(day=last_day)
        return key + datetime.timedelta(days=6)  # week end (Sun)

    def _period_label(self, key: datetime.date, group: str) -> str:
        if group == 'month':
            return key.strftime('%Y-%m')
        iso = key.isocalendar()
        return f"W{iso.week:02d} {iso.year}"  # ✅ ISO year (ważne na przełomie roku)

    def _add_month(self, d: datetime.date) -> datetime.date:
        # d jest zawsze pierwszym dniem miesiąca
        y, m = d.year, d.month
        if m == 12:
            return datetime.date(y + 1, 1, 1)
        return datetime.date(y, m + 1, 1)

    def _generate_period_keys(self, axis_start: datetime.date, axis_end: datetime.date, group: str):
        """
        Generuje wszystkie klucze okresów (week_start lub month_start) pokrywające zakres axis_start..axis_end.
        Dzięki temu masz ciągłą oś czasu nawet gdy w okresie nie było dostaw (wtedy 0).
        """
        keys = []

        if group == 'week':
            k = self._week_start(axis_start)
            while k <= axis_end:
                keys.append(k)
                k += datetime.timedelta(days=7)
            return keys

        # month
        k = self._month_start(axis_start)
        end_k = self._month_start(axis_end)
        while k <= end_k:
            keys.append(k)
            k = self._add_month(k)
        return keys

    def get(self, request):
        # 1) Parametry
        today = now().date()
        year_start = datetime.date(today.year, 1, 1)

        start_param = request.GET.get('start')  # 'dd-mm-yyyy'
        end_param = request.GET.get('end')      # 'dd-mm-yyyy'
        group = (request.GET.get('group') or 'week').lower()
        if group not in ('week', 'month'):
            group = 'week'

        start_raw = self._parse_date(start_param, year_start)
        end_raw = self._parse_date(end_param, today)
        if end_raw < start_raw:
            start_raw, end_raw = end_raw, start_raw

        # ✅ do bazy: nie cofamy do poniedziałku / 1 dnia miesiąca
        filter_start = start_raw
        filter_end = end_raw

        # ✅ do osi czasu (generowanie okresów): możemy “cofnąć” do początku okresu
        axis_start = self._week_start(start_raw) if group == 'week' else self._month_start(start_raw)
        axis_end = end_raw

        # 2) Dane – JEDEN queryset + prefetch
        deliveries_qs = (
            Delivery.objects
            .filter(date__gte=filter_start, date__lte=filter_end)
            .select_related('provider')
            .prefetch_related(
                Prefetch(
                    'deliveryitem_set',
                    queryset=DeliveryItem.objects
                    .select_related('order__customer')
                    .only('delivery_id', 'quantity', 'order__dimensions', 'order__customer__name')
                )
            )
        )

        # 3) Agregacja per okres + dostawcy/klienci
        totals_by_period = defaultdict(int)
        orders_by_provider = defaultdict(int)
        orders_by_customer = defaultdict(int)

        for d in deliveries_qs:
            delivery_area = 0
            for item in d.deliveryitem_set.all():
                a = item.calculate_area() or 0
                delivery_area += a

                try:
                    customer = item.order.customer.name
                    orders_by_customer[customer] += int(round(a, 0))
                except AttributeError:
                    pass

            area = int(round(delivery_area, 0))

            key = self._week_start(d.date) if group == 'week' else self._month_start(d.date)
            totals_by_period[key] += area

            if getattr(d, 'provider', None):
                orders_by_provider[d.provider.name] += area

        # 4) ✅ Generowanie osi czasu (bez dziur) + serie
        period_keys = self._generate_period_keys(axis_start, axis_end, group)

        dates = []
        period_labels = []
        values_by_period = []
        values_cumulative = []
        cum = 0

        for k in period_keys:
            total = int(totals_by_period.get(k, 0))  # ✅ brak okresu => 0
            cum += total
            values_by_period.append(total)
            values_cumulative.append(cum)

            # koniec okresu do wykresu (możesz też clampować do end_raw jeśli wolisz)
            period_end = self._period_key_end(k, group)
            # clamp, żeby nie “wychodziło” poza zakres, jeśli Ci to przeszkadza na osi
            period_end = min(period_end, end_raw)

            dates.append(period_end)
            period_labels.append(self._period_label(k, group))

        total_amount = sum(values_by_period)
        cel = 2_000_000
        ile = max(cel - total_amount, 0)

        year_days = 365 + calendar.isleap(today.year)
        days_left = year_days - today.timetuple().tm_yday

        customer_results = sorted(orders_by_customer.items(), key=lambda x: x[0])
        customer_labels = [k for k, _ in customer_results]
        customer_values = [v for _, v in customer_results]

        provider_results = sorted(orders_by_provider.items(), key=lambda x: x[0])
        provider_labels = [k for k, _ in provider_results]
        provider_values = [v for _, v in provider_results]

        context = {
            "group": group,
            # pokazuj realnie wybrany zakres (bez cofania do poniedziałku)
            "start": start_raw,
            "end": end_raw,

            "dates": dates,
            "period_labels": period_labels,
            "values_by_period": values_by_period,
            "values": values_cumulative,

            "total_amount": total_amount,
            "cel": cel,
            "ile": ile,
            "days_left": days_left,

            "customer_labels": customer_labels,
            "customer_values": customer_values,
            "provider_labels": provider_labels,
            "provider_values": provider_values,
        }
        return render(request, self.template_name, context)


class StockView(LoginRequiredMixin, View):
    login_url = reverse_lazy('login')

    def get(self, request, stock_id):
        stock = Stock.objects.get(id=stock_id)
        try:
            customer, flute, dimensions, name = list(map(lambda x: x.strip(), stock.name.split('|')))
            product = Product.objects.get(name=stock.name)
            orders = Order.objects.filter(product=product)
            product_supplies = StockSupply.objects.filter(name=stock.name)
        except ValueError:
            dimensions = stock.name.split('[')[1].replace(']', '').lower()
            supplies = StockSupply.objects.filter(dimensions=dimensions)
        history = WarehouseStockHistory.objects.filter(warehouse_stock__stock=stock)
        return render(request, 'warehouse/stock-details.html', locals())


class WarehouseStockView(LoginRequiredMixin, View):
    login_url = reverse_lazy('login')

    def get(self, request, warehouse_stock_id):
        warehouse_stock = WarehouseStock.objects.get(id=warehouse_stock_id)
        history = []
        stock_increases = StockSupplySettlement.objects.filter(stock_supply__name=warehouse_stock.stock.name)
        stock_decreases = StockSupplySell.objects.filter(stock_supply__name=warehouse_stock.stock.name)

        for s in stock_increases:
            record = (s.settlement.settlement_date, s.quantity, True)
            history.append(record)
        for s in stock_decreases:
            record = (s.sell.date, s.quantity, False)
            history.append(record)

        history = sorted(history, key=lambda x:x[0])

        supplies = warehouse_stock.fifo()

        return render(request, 'warehouse/warehouse-stock-details.html', locals())



class LoadDeliveryToGSFile(LoginRequiredMixin, View):
    login_url = reverse_lazy('login')

    def get(self, request, delivery_id):
        delivery = Delivery.objects.get(id=delivery_id)
        items = DeliveryItem.objects.filter(delivery=delivery, updated=False)
        # numbers = []
        # values = []
        data = {}
        for item in items:
            item.updated = True
            item.save()
            order_id = item.order.order_id
            number, year = map(int, order_id.split('/'))
            if len(str(year)) == 2:
                year = '20' + str(year)
            else:
                year = str(year)
            if year in data.keys():
                data[year][0].append(number)
                data[year][1].append(item.quantity)
            else:
                data[year] = [[number], [item.quantity]]
            # numbers.append(number)
            # values.append(item.quantity)

        for year_key in data.keys():
            numbers, values = data[year_key]
            if all((numbers, values)):
                get_rows_numbers(numbers, int(year_key), delivery.provider, values)

        delivery.updated = True
        delivery.save()

        return redirect("warehouse:delivery-detail-view", delivery_id=delivery_id)


class SellProductList(LoginRequiredMixin, View):
    login_url = reverse_lazy('login')

    def get(self, request):
        sells = (
            ProductSell3.objects
            .select_related("product", "warehouse_stock__stock", "warehouse_stock__warehouse", "customer")
            .order_by("-date", 'customer', 'product')
        )

        warehouse_stocks = (
            WarehouseStock.objects
            .select_related("stock", "warehouse")
            .filter(
                quantity__gt=0,
                warehouse__in=(Warehouse.objects.filter(
                    name__in=("MAGAZYN WYROBÓW GOTOWYCH", "MAGAZYN MATERIAŁÓW POMOCNICZYCH", 'MAGAZYN GŁÓWNY')))
            )
            .order_by("-warehouse", "stock__name")
        )

        context = {
            "warehouse_stocks": warehouse_stocks,
            "products": Product.objects.all().order_by("name"),  # do <select> w modalu
            "customers": Buyer.objects.all().order_by("name"),
            "sells": sells
        }
        return render(request, "warehouse/sell-product-list.html", context=context)


class ProductSell3CreateView(LoginRequiredMixin, CreateView):
    login_url = reverse_lazy('login')

    model = ProductSell3
    fields = ["warehouse_stock", "quantity", "customer", "price", "date", "customer_alter_name"]

    def get_success_url(self):
        return reverse("warehouse:sells-list-view")

    def form_valid(self, form):
        with transaction.atomic():
            ws = (
                WarehouseStock.objects
                .select_for_update()
                .select_related("stock", "warehouse")
                .get(pk=form.cleaned_data["warehouse_stock"].pk)
            )
            qty = form.cleaned_data["quantity"]

            if qty <= 0:
                form.add_error("quantity", "Ilość musi być większa od zera.")
                return self.form_invalid(form)
            if ws.quantity < qty:
                form.add_error("quantity", "Nie ma wystarczającej ilości w magazynie!")
                return self.form_invalid(form)

            sell = form.save(commit=False)
            sell.customer_alter_name = form.cleaned_data["customer_alter_name"]
            sell.warehouse_stock = ws
            # product zostanie ustawiony automatycznie w clean()/save()
            sell.full_clean()  # uruchomi walidacje z modelu (w tym auto-resolve product)
            sell.save()

            before = ws.quantity
            after = before - qty
            WarehouseStockHistory.objects.create(
                warehouse_stock=ws,
                quantity_before=before,
                quantity_after=after,
                date=form.cleaned_data["date"],
            )
            ws.quantity = after
            ws.save(update_fields=["quantity"])

        messages.success(self.request, "Sprzedaż zapisana.")
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        print(form.errors)
        print(form.cleaned_data)
        return redirect(self.get_success_url())


class PaletteView(LoginRequiredMixin, View):
    login_url = reverse_lazy('login')

    def get(self, request):
        palettes = Palette.objects.all()
        customers = Buyer.objects.all().exclude(name__in=["JASS", "TFP"])

        # 1. Dane klientów (pomijamy dostawców JASS, TFP)
        customer_palette_map = {
            (cp.customer_id, cp.palette_id): cp.quantity
            for cp in CustomerPalette.objects.exclude(customer__name__in=["JASS", "TFP"])
        }

        header = [''] + [p.name for p in palettes]
        result = []

        for customer in customers:
            row = [customer]
            for palette in palettes:
                quantity = customer_palette_map.get((customer.id, palette.id), '-')
                row.append(quantity)
            result.append(row)

        # 2. Stan bazowy dostawców (z CustomerPalette)
        provider_inventory = defaultdict(dict)

        for cp in CustomerPalette.objects.filter(customer__name__in=["JASS", "TFP"]):
            provider_inventory[cp.customer.name][cp.palette.name] = cp.quantity

        # 3. Data synchronizacji
        try:
            sync = LocalSetting.objects.get(name="delivery_sync")
            sync_date = datetime.datetime.strptime(sync.value, "%d-%m-%Y").date()
        except (LocalSetting.DoesNotExist, ValueError):
            sync_date = now().date()

        # 4. Dostawy od daty synchronizacji
        providers = Provider.objects.filter(name__in=["JASS", "TFP"])
        provider_deliveries = defaultdict(dict)

        for provider in providers:
            # wszystkie dostawy danego providera od daty synchronizacji
            deliveries = Delivery.objects.filter(provider=provider, date__gte=sync_date)

            # sumujemy dostarczone palety
            delivery_palettes = (
                DeliveryPalette.objects
                .filter(delivery__in=deliveries)
                .values('palette__name')
                .annotate(total=Sum('quantity'))
            )

            for dp in delivery_palettes:
                pname = provider.name
                palette_name = dp['palette__name']
                quantity = dp['total']

                # zapisz same dostawy
                provider_deliveries[pname][palette_name] = quantity

                # dodaj do stanu końcowego (bazowy + dostawy)
                if palette_name in provider_inventory[pname]:
                    provider_inventory[pname][palette_name] += quantity
                else:
                    provider_inventory[pname][palette_name] = quantity

        # 5. Kontekst
        context = {
            'header': header,
            'result': result,
            'provider_deliveries': dict(provider_deliveries),  # same dostawy
            'provider_inventory': dict(provider_inventory),  # stan po bazie + dostawach
            'sync_date': sync_date,
        }

        return render(request, 'warehouse/palette.html', context)


# from django.contrib import messages
# from django.shortcuts import render, redirect
# from django.urls import reverse_lazy
# from django.views import View
#
# from .forms import ManuallyOrdersForm
# from .models import Provider
# from .utils import load_orders   # przykładowo, dostosuj import


class AddOrdersManually(LoginRequiredMixin, View):
    login_url = reverse_lazy('login')

    def get_context_data(self, form=None):
        if form is None:
            form = ManuallyOrdersForm()

        providers = Provider.objects.all()
        numbers = [n for n in range(1, 1000)]
        rows = [r for r in range(1, 3000)]

        return {
            'providers': providers,
            'numbers': numbers,
            'rows': rows,
            'orders_form': form,
        }

    def get(self, request):
        context = self.get_context_data()
        return render(request, 'warehouse/add_orders.html', context=context)

    def post(self, request):
        form = ManuallyOrdersForm(request.POST)

        if form.is_valid():
            source = form.cleaned_data['source']

            try:
                if source == 'sheet':
                    row = form.cleaned_data['sheet_row']
                    year = form.cleaned_data['year']
                    result = load_orders(int(year), row=int(row) - 1, division=None, row_list=None)
                    messages.success(
                        request,
                        f'Pomyślnie załadowano zamówienia z wiersza {row}.'
                        f'{result}'
                    )

                elif source == 'provider':
                    provider = form.cleaned_data['provider']
                    order_no = form.cleaned_data['provider_order_number']
                    year = form.cleaned_data['year']
                    # tutaj Twoja funkcja np.:
                    # count = import_from_provider(provider, order_no)
                    print(provider, order_no)
                    messages.success(
                        request,
                        f'Pomyślnie załadowano zamówienie {order_no} od dostawcy {provider}.'
                    )
                    z = get_rows_numbers2([int(order_no)], int(year), provider)
                    load_orders(int(year), row_list=z)

                # po sukcesie: redirect, żeby uniknąć ponownego POSTa po F5
                return redirect('warehouse:add-orders')  # podmień na swoją nazwę URL

            except Exception as e:
                # Błąd w trakcie importu (np. problem z API, bazą itd.)
                messages.error(
                    request,
                    f'Wystąpił błąd podczas importu zamówień: {e}'
                )
                context = self.get_context_data(form=form)
                return render(request, 'warehouse/add_orders.html', context=context)

        # jeśli formularz jest niepoprawny
        messages.error(request, 'Formularz zawiera błędy. Popraw je i spróbuj ponownie.')
        context = self.get_context_data(form=form)
        return render(request, 'warehouse/add_orders.html', context=context)



def add_product_sell3(request):
    if request.method == "POST":
        print("add sell")
        with transaction.atomic():
            product = Product.objects.get(id=int(request.POST.get("product")))
            customer = Buyer.objects.get(id=int(request.POST.get("customer")))
            customer_alter_name = request.POST.get("customer_alter_name")
            warehouse_stock = WarehouseStock.objects.get(id=int(request.POST.get("warehouse_stock")))
            order = Order.objects.get(id=int(request.POST.get("order")))
            quantity = request.POST.get("quantity_sell")
            date = request.POST.get("date_sell")
            sale = ProductSell3.objects.create(
                product=product,
                customer=customer,
                customer_alter_name=customer_alter_name,
                warehouse_stock=warehouse_stock,
                order=order,
                quantity=quantity,
                price=request.POST.get("price_sell"),
                date=date,
            )

            WarehouseStockHistory.objects.create(
                warehouse_stock=warehouse_stock,
                quantity_before=warehouse_stock.quantity,
                quantity_after=warehouse_stock.quantity - int(quantity),
                date=date
            )

            if order:
                stock_supply = None
                stock_supply_settlements = StockSupplySettlement.objects.filter(settlement__order=order, as_result=True)
                if len(stock_supply_settlements) == 1:
                    stock_supply = stock_supply_settlements[0].stock_supply
                    stock_supply.used = True
                    stock_supply.save()
                StockSupplySell.objects.create(
                    stock_supply=stock_supply,
                    sell=sale,
                    quantity=int(quantity)
                )

            # StockSupplySell.objects.create(
            #     stock_supply = StockSupply.objects.get(deli)
            # )

            # warehouse_stock.show_all_stock_supplies()

            warehouse_stock.quantity -= int(quantity)
            product.price = request.POST.get("price_sell")
            product.save()

            warehouse_stock.save()

        return redirect(request.META.get('HTTP_REFERER', '/'))


def assign_products_to_orders(year=None, row=None, division=None):
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
    year = 2025
    data_all = get_all(str(year)) if year else get_all(str(datetime.datetime.today().year))
    result = ''
    row = row if row else 100
    division = division if division else '10, 1500'

    if division:
        start, end = division.split(',')
        rows = [r for r in range(int(start), int(end) + 1)]
    else:
        rows = [row]

    for row in rows:
        try:
            data = data_all[row]

            # Klucze identyfikujące zlecenie
            provider_code = data[0].upper().strip()
            order_id = f'{data[1].upper().strip()}/{data[2].upper().strip()}'

            # Szukamy istniejącego zlecenia BEZ przypisanego produktu
            try:
                order = Order.objects.get(order_id=order_id, provider__shortcut=provider_code, product__isnull=True)
            except Order.DoesNotExist:
                # result += f'Order {provider_code}/{order_id} already has product or does not exist<br>'
                continue

            # Tworzymy dane produktu
            customer_name = data[18].upper().strip()
            flute = get_flute(data[19].upper().strip())
            dimensions = f'{data[12].strip()}x{data[13].strip()}'
            product_additional_name = data[24].upper().strip()
            product_name = f'{customer_name} | {flute} | {data[23].lower().strip()} | {product_additional_name}'

            if not all((product_name, dimensions, flute)):
                result += f'Incomplete product data in row {row}<br>'
                continue

            # Szukamy lub tworzymy produkt
            product, _ = Product.objects.get_or_create(
                name=product_name,
                defaults={
                    'dimensions': dimensions,
                    'flute': flute,
                    'gsm': 0  # możesz podmienić na konkretną wartość jeśli dostępna
                }
            )

            # Przypisujemy produkt do zlecenia
            order.product = product
            order.save()
            result += f'Order {provider_code}/{order_id} updated with product<br>'

        except Exception as e:
            result += f'Error in row {row}: {e}<br>'

    return HttpResponse(result)


def assign_price_to_orders(request):
    year = 2025
    data_all = get_all(str(year)) if year else get_all(str(datetime.datetime.today().year))
    result = ''
    division = '10, 1500'
    start, end = division.split(',')
    rows = [r for r in range(int(start), int(end) + 1)]

    for row in rows:
        try:
            data = data_all[row]

            # Klucze identyfikujące zlecenie
            provider_code = data[0].upper().strip()
            order_id = f'{data[1].upper().strip()}/{data[2].upper().strip()}'

            # Szukamy istniejącego zlecenia BEZ przypisanego produktu
            try:
                order = Order.objects.get(order_id=order_id, provider__shortcut=provider_code)
            except Order.DoesNotExist:
                # result += f'Order {provider_code}/{order_id} already has product or does not exist<br>'
                continue
            if not order.price:
                price = int(float(data[22].upper().strip().replace('\xa0', '').replace(',', '.'))) if data[
                    22] else 0
                if price:
                    order.price = price
                    order.save()
                    result += f'Order {provider_code}/{order_id} updated with price<br>'
                else:
                    result += f'Order {provider_code}/{order_id} no price<br>'

            if not order.order_date:
                order_date = data[6].upper().strip() if data[6].upper().strip() else None
                order_year = data[5][:4] if data[5] else data[6][:4]

                order.order_date = order_date
                order.order_year = order_year

                if order_date:
                    result += f'Order {provider_code}/{order_id} updated with date<br>'
                    order.save()
                else:
                    result += f'Order {provider_code}/{order_id} no date<br>'

        except Exception as e:
            result += f'Error in row {row}: {e}<br>'

    return HttpResponse(result)


def clear_orders(request):
    orders = Order.objects.all()

    for o in orders:
        o.delivered_quantity = 0
        o.delivery_date = None
        o.delivered = False
        o.finished = False
        o.save()
