# warehouse/views.py

from django.views.generic import ListView
from warehouse.services.products import safe_get_or_create_product
from warehouse.forms import WarehouseStockFifoSellForm
from django.shortcuts import HttpResponse
from django.views import View
from django.http import JsonResponse
from django.db.models.deletion import ProtectedError
from django.views.generic import CreateView, DetailView
from django.urls import reverse
from warehouse.gs_connection import *
from warehouse.models import *
from warehouse.forms import DeliveryItemForm, DeliveryForm, DeliveryPaletteFormSet, DeliverySpecialItemForm, ManuallyOrdersForm
from warehousemanager.models import Buyer, LocalSetting
from production.models import ProductionOrder, ProductionUnit
import pdfplumber
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.middleware.csrf import get_token
import calendar
from collections import defaultdict
from django.shortcuts import render
from django.utils.timezone import now
from django.db.models import Prefetch
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from warehouse.services.bom_preview import bom_preview_for_order
from warehouse.services.bom_realization import realize_order_bom
from warehouse.services.stock_moves import rebuild_ws_history_from_date
from warehouse.models import attach_origin_orders_to_sell
from warehousemanager.functions import visit_counter
from django.utils.dateparse import parse_date
import datetime
import secrets
from django.conf import settings
from warehouse.models import BOM, Order
from warehouse.forms import OrderFromBOMForm
from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.db.models import Sum
from django.core.exceptions import ValidationError
import logging
from django.core.exceptions import PermissionDenied

logger = logging.getLogger(__name__)


def create_shipment_unit_history(*, shipment_unit, user, action):
    return ShipmentUnitHistory.objects.create(
        shipment_unit=shipment_unit,
        shipment_unit_original_id=shipment_unit.id,
        order=shipment_unit.order,
        product=shipment_unit.product,
        palette=shipment_unit.palette,
        quantity=shipment_unit.quantity,
        action=action,
        changed_by=user,
    )


class ShipmentUnitOwnerRequiredMixin:
    shipment_unit_url_kwarg = "shipment_unit_id"

    def get_shipment_unit(self):
        if not hasattr(self, "_shipment_unit"):
            self._shipment_unit = get_object_or_404(
                ShipmentUnit.objects.select_related(
                    "order",
                    "product",
                    "palette",
                    "created_by",
                ),
                id=self.kwargs[self.shipment_unit_url_kwarg],
            )

        return self._shipment_unit

    def check_shipment_unit_permission(self):
        shipment_unit = self.get_shipment_unit()
        user = self.request.user

        if user.is_superuser:
            return

        if shipment_unit.created_by_id == user.id:
            return

        raise PermissionDenied(
            "Nie masz uprawnień do zmiany tej jednostki wysyłkowej."
        )


def _check_undo_password(request):
    password = request.POST.get("confirm_password", "") or ""
    expected = settings.UNDO_OPERATIONS_PASSWORD or ""

    if not expected:
        raise ValueError("Brak konfiguracji UNDO_OPERATIONS_PASSWORD.")

    return secrets.compare_digest(password, expected)


def undo_delivery_item_process(request, item_id):
    if request.method != "POST":
        return redirect(request.META.get("HTTP_REFERER", "/"))

    if not _check_undo_password(request):
        messages.error(request, "Nieprawidłowe hasło do cofania operacji.")
        return redirect(request.META.get("HTTP_REFERER", "/"))

    try:
        with transaction.atomic():
            item = DeliveryItem.objects.select_for_update().get(pk=item_id)

            if not item.processed:
                raise ValidationError("Ta pozycja dostawy nie jest jeszcze przyjęta na magazyn.")

            supply = (
                StockSupply.objects
                .select_for_update()
                .filter(delivery_item=item)
                .first()
            )

            if not supply:
                raise ValidationError("Brak StockSupply dla tej pozycji dostawy.")

            settled_qty = (
                StockSupplySettlement.objects
                .filter(stock_supply=supply, as_result=False)
                .aggregate(s=Sum("quantity"))["s"] or 0
            )
            sold_qty = (
                StockSupplySell.objects
                .filter(stock_supply=supply)
                .aggregate(s=Sum("quantity"))["s"] or 0
            )

            if settled_qty > 0 or sold_qty > 0:
                raise ValidationError(
                    f"Nie można cofnąć przyjęcia. Partia była już użyta "
                    f"(rozliczono: {settled_qty}, sprzedano: {sold_qty})."
                )

            hist_rows = list(
                WarehouseStockHistory.objects
                .select_for_update()
                .filter(stock_supply=supply)
                .order_by("date", "id")
            )

            touched_ws_ids = {h.warehouse_stock_id for h in hist_rows}
            delivery_date = item.delivery.date

            WarehouseStockHistory.objects.filter(stock_supply=supply).delete()
            supply.delete()

            for ws_id in touched_ws_ids:
                ws = WarehouseStock.objects.select_for_update().get(pk=ws_id)
                rebuild_ws_history_from_date(ws=ws, from_date=delivery_date)

            order = Order.objects.select_for_update().get(pk=item.order_id)
            qty = int(item.quantity or 0)

            order.delivered_quantity = max(0, int(order.delivered_quantity or 0) - qty)
            order.delivered = bool(order.order_quantity and (order.delivered_quantity / order.order_quantity) > 0.92)

            last_processed_item = (
                DeliveryItem.objects
                .filter(order=order, processed=True)
                .exclude(pk=item.pk)
                .select_related("delivery")
                .order_by("-delivery__date", "-id")
                .first()
            )
            order.delivery_date = last_processed_item.delivery.date if last_processed_item else None
            order.save(update_fields=["delivered_quantity", "delivered", "delivery_date"])

            item.processed = False
            item.save(update_fields=["processed"])

            delivery = Delivery.objects.select_for_update().get(pk=item.delivery_id)
            if not DeliveryItem.objects.filter(delivery=delivery, processed=True).exists():
                delivery.processed = False
                delivery.save(update_fields=["processed"])

        messages.success(request, "Przyjęcie na magazyn zostało cofnięte.")
    except Exception as e:
        messages.error(request, f"Błąd cofania przyjęcia: {e}")

    return redirect(request.META.get("HTTP_REFERER", "/"))


def get_flute(text):
    text = (text or "").upper()
    waves = 0

    for letter in text:
        if letter == '3':
            waves = 3
            break
        elif letter == '5':
            waves = 5
            break

    if waves == 3:
        if 'E' in text:
            return 'E'
        if 'B' in text:
            return 'B'
        if 'C' in text:
            return 'C'
    elif waves == 5:
        if 'EB' in text:
            return 'EB'
        if 'BC' in text:
            return 'BC'
        if 'EE' in text:
            return 'EE'

    return None


def build_product_name(customer_name, flute, sheet_name, extra):
    sheet_name = (sheet_name or "").lower().strip()
    extra = (extra or "").upper().strip()

    if extra:
        return f"{customer_name} | {flute} | {sheet_name} | {extra}"
    return f"{customer_name} | {flute} | {sheet_name}"


def find_existing_product(product_name, dimensions=None, flute=None):
    qs = Product.objects.filter(name=product_name)

    if flute:
        qs = qs.filter(flute=flute)

    return qs.first()


def load_orders(year, row=None, division=None, row_list=None, preview_only=False):
    year = year if year else datetime.datetime.today().year
    data_all = get_all(year) if year else get_all(str(datetime.datetime.today().year))
    result = ""

    row = row if row is not None else None
    division = division if division else None

    if division:
        start, end = division.split(",")
        rows = [r for r in range(int(start), int(end) + 1)]
    elif row is not None:
        rows = [row]
    else:
        rows = []

    if row_list:
        rows = row_list

    new_products = []
    seen_new_products = set()

    for row in rows:
        try:
            data = data_all[row]

            customer_name = data[18].upper().strip()
            provider_shortcut = data[0].upper().strip()
            order_name = data[19].upper().strip()
            flute = get_flute(order_name)
            product_dimensions = f"{data[12].strip()}x{data[13].strip()}"
            sheet_name = (data[23] or "").strip()
            extra = data[24].upper().strip() if data[24] else ""
            order_id = f"{data[1].upper().strip()}/{data[2].upper().strip()}"

            product_name = build_product_name(
                customer_name=customer_name,
                flute=flute,
                sheet_name=sheet_name,
                extra=extra
            )

            try:
                customer = Buyer.objects.get(name=customer_name)
            except Buyer.DoesNotExist:
                if preview_only:
                    customer = None
                else:
                    customer = Buyer(
                        name=customer_name,
                        shortcut=customer_name[:5]
                    )
                    customer.save()

            try:
                provider = Provider.objects.get(shortcut=provider_shortcut)
            except Provider.DoesNotExist:
                if preview_only:
                    provider = None
                else:
                    provider = Provider(
                        name=data[0],
                        shortcut=data[0]
                    )
                    provider.save()

            product = find_existing_product(
                product_name=product_name,
                dimensions=product_dimensions,
                flute=flute
            )

            if not product:
                product_key = (product_name, product_dimensions, flute)

                if preview_only:
                    if product_key not in seen_new_products:
                        seen_new_products.add(product_key)
                        new_products.append({
                            "customer_name": customer_name,
                            "product_name": product_name,
                            "flute": flute,
                            "dimensions": product_dimensions,
                            "extra": extra,
                            "row": row + 1,
                            "order_id": order_id,
                            "order_name": order_name,
                        })

                    result += (
                        f"NOWY PRODUKT: {product_name} | "
                        f"{product_dimensions} | {flute}<br>\n"
                    )
                    continue
                else:
                    product = safe_get_or_create_product(
                        customer_name,
                        flute,
                        sheet_name,
                        extra
                    )

            try:
                order = Order.objects.get(
                    order_id=order_id,
                    provider__shortcut=provider_shortcut
                )
                result += f"{order} already exists<br>\n"

            except Order.DoesNotExist:
                price = (
                    int(float(data[22].upper().strip().replace('\xa0', '').replace(',', '.')))
                    if data[22] else 0
                )
                order_date = data[6].upper().strip() if data[6].upper().strip() else None

                order = Order(
                    customer=customer,
                    provider=provider,
                    order_id=order_id,
                    customer_date=data[5].upper().strip() if data[5].upper().strip() else data[6].upper().strip(),
                    order_date=order_date,
                    order_year=data[5][:4] if data[5] else data[6][:4],
                    delivery_date=None,
                    production_date=None,
                    dimensions=product_dimensions,
                    name=order_name,
                    weight=0,
                    order_quantity=data[14].upper().strip(),
                    delivered_quantity=data[15].upper().strip() if data[15].upper().strip() else 0,
                    price=price,
                    product=product,
                )

                if price and order_date:
                    order.save()
                    result += f"{order} saved<br>"
                elif provider and provider.name == "PAKER":
                    order.price = 0
                    order.save()
                    result += f"{order} saved<br>"
                else:
                    result += f"{order_id} no cardboard price or order date<br>\n"

        except Exception as e:
            result += f"{e}<br>\n"

    return {
        "result": result,
        "new_products": new_products,
    }


def delete_delivery_ajax(request, delivery_id):
    user = request.user
    if user.has_perm('warehouse.delete_delivery'):
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


def parse_wz_pdf(pdf_file):
    errors = []
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

    with pdfplumber.open(pdf_file) as pdf:
        all_text = ""
        for page in pdf.pages:
            print(type(page.extract_text()))
            text = page.extract_text() or ""
            all_text += text + "\n"

    lines = all_text.splitlines()

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
                p_line = line.split(' ')
                palettes = f'{p_line[0]};{p_line[1]};{p_line[3].split(",")[0]}'
                palletes_list.append(palettes)
            if "Nr zam. klienta:" in line:
                number = line.split("Nr zam. klienta:")[1].strip().split(" ")[0].strip()
                new_num = ""
                for n in number:
                    if n.isdigit() or n == '/':
                        new_num += n
                number = new_num
                orders.append([number, cardboard, dimensions, quantity])
            if len(line.split(' ')) == 5 or len(line.split(' ')) == 6:
                line_split = line.split(' ')
                if line_split[0][0].isdigit() and line_split[1][-1] == '\xad' and 'x' in line_split[2]:
                    cardboard = line_split[1][:-1]
                    dimensions = line_split[2]
                    quantity = (
                        line_split[3].split(',')[0]
                        if len(line_split) == 5
                        else f'{line_split[3]}{line_split[4]}'.split(',')[0]
                    )

            if "Ilość na palecie: " in line:
                if order_num == len(orders):
                    p_quantity += f'{line.split("palecie:")[1].split(",")[0].strip().replace(" ", "")};'
                else:
                    orders[-2].append(p_quantity)
                    order_num += 1
                    p_quantity = f'{line.split("palecie:")[1].split(",")[0].strip().replace(" ", "")};'

        if orders:
            orders[-1].append(p_quantity)

        date = date.replace('­', '.').split('.')
        if int(date[0]) > 31:
            date = (date[2], date[1], date[0])

    elif 'AQUILA' in all_text or 'aquila' in all_text:

        for num in range(len(lines)):
            line = lines[num]

            if not provider and 'aquila' in line.lower():
                provider = 'AQ'

            if not wz_number and "PAKER SPÓŁKA Z OGRANICZONĄ" in line:
                s_line = line.split(' ')
                wz_number = s_line[-2]
                date = s_line[-1].split('/')

            if not phone and "Nr tel./rejestracyjny" in line:
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
                if len(order_num_line.split(' ')) > 1:
                    order_num = order_num_line.split(' ')[1]
                else:
                    order_num = order_num_line[2:]
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

        if order_data:
            orders.append(order_data)

    else:
        for num in range(len(lines)):
            line = lines[num]
            if 'JASSBOARD SP. Z O.O.' in line:
                provider = "JASS"
            if "Data wystawienia: " in line:
                date = line.split('wystawienia: ')[1].strip().replace('-', '.').split('.')
                date = (date[2], date[1], date[0])
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
                if len(number.split('/')[1]) > 2:
                    _num, _year = number.split('/')
                    number = _num + '/' + _year[:2]
                if number not in order_numbers:
                    order_numbers.append(number)
            if "ark" in line and 'm2' in line and "RAZEM" not in line and 'Ilość wysłana' not in line:
                cardboard_line = line.split(' ')
                cardboard = cardboard_line[1][:-9] if cardboard_line[1][2].isdigit() else cardboard_line[1][:-8]
                dimensions = cardboard_line[1][-9:] if cardboard_line[1][2].isdigit() else cardboard_line[1][-8:]
                p_quantity += (
                    f'{cardboard_line[3]};'
                    if len(cardboard_line) == 7
                    else f'{cardboard_line[3]}{cardboard_line[4]};'
                )
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

    if not provider:
        errors.append("Nie udało się rozpoznać dostawcy z pliku WZ.")

    return {
        "provider": provider,
        "wz_number": wz_number,
        "car_number": car_number,
        "date": date,
        "phone": phone,
        "orders": orders,
        "palletes_list": palletes_list,
        "errors": errors,
    }


def collect_new_products_for_wz(parsed):
    errors = []
    all_new_products = []

    provider_shortcut = parsed["provider"]
    orders = parsed["orders"]

    if not provider_shortcut:
        errors.append("Nie udało się rozpoznać dostawcy z pliku WZ.")
        return {
            "new_products": [],
            "errors": errors,
        }

    try:
        provider_obj = Provider.objects.get(shortcut=provider_shortcut)
    except Provider.DoesNotExist:
        errors.append(f"Provider {provider_shortcut} does not exist.")
        return {
            "new_products": [],
            "errors": errors,
        }

    wrong_orders = []
    year_orders = {}
    seen = set()

    for o in orders:
        try:
            order_num_split, year_num_split = o[0].split('/')

            if len(year_num_split) != 2:
                cleaned_year = ""
                for char in year_num_split:
                    if char.isnumeric():
                        cleaned_year += char
                year_num_split = cleaned_year

            if len(year_num_split) == 2:
                year_num_split = '20' + year_num_split

            year_orders.setdefault(year_num_split, []).append(int(order_num_split))

        except Exception:
            errors.append(f'Error creating item: {o}')
            wrong_orders.append(o)

    for key in year_orders:
        nums = get_rows_numbers2(year_orders[key], int(key), provider_obj)
        preview = load_orders(int(key), row_list=nums, preview_only=True)

        for p in preview["new_products"]:
            unique_key = (p["product_name"], p["dimensions"], p["flute"])
            if unique_key not in seen:
                seen.add(unique_key)
                all_new_products.append(p)

    return {
        "new_products": all_new_products,
        "errors": errors,
    }


class LoadWZ(PermissionRequiredMixin, View):
    permission_required = "warehouse.add_delivery"
    login_url = reverse_lazy('login')

    def get(self, request):
        print('#1')
        return render(request, "warehouse/load_wz.html")

    def post(self, request):
        confirm_new_products = request.POST.get("confirm_new_products") == "1"

        try:
            # ETAP 2 — po potwierdzeniu bierzemy dane z session
            if confirm_new_products:
                parsed = request.session.get("pending_wz_parsed")

                if not parsed:
                    return render(request, "warehouse/load_wz_result.html", {
                        "errors": ["Brak danych oczekującego WZ. Wgraj plik ponownie."]
                    })

                response = self._save_wz(request, parsed)

                try:
                    del request.session["pending_wz_parsed"]
                except KeyError:
                    pass

                return response

            # ETAP 1 — pierwszy upload i preview
            if "wz_file" not in request.FILES:
                return render(request, "warehouse/load_wz_result.html", {
                    "errors": ["No file was uploaded. Please select a file and try again."]
                })

            pdf_file = request.FILES["wz_file"]
            parsed = parse_wz_pdf(pdf_file)

            if parsed["errors"]:
                return render(request, "warehouse/load_wz_result.html", {
                    "errors": parsed["errors"]
                })

            preview = collect_new_products_for_wz(parsed)

            if preview["errors"]:
                return render(request, "warehouse/load_wz_result.html", {
                    "errors": preview["errors"]
                })

            # zapisujemy sparsowane dane do session
            request.session["pending_wz_parsed"] = parsed
            request.session.modified = True

            if preview["new_products"]:
                return render(request, "warehouse/confirm_new_products_wz.html", {
                    "new_products": preview["new_products"],
                })

            response = self._save_wz(request, parsed)

            try:
                del request.session["pending_wz_parsed"]
            except KeyError:
                pass

            return response

        except Exception as e:
            return render(request, "warehouse/load_wz_result.html", {
                "errors": [f"Wystąpił błąd podczas przetwarzania WZ: {e}"]
            })

    def _save_wz(self, request, parsed):
        result = []
        errors = []

        provider = parsed["provider"]
        wz_number = parsed["wz_number"]
        car_number = parsed["car_number"]
        date = parsed["date"]
        phone = parsed["phone"]
        orders = parsed["orders"]
        palletes_list = parsed["palletes_list"]

        try:
            delivery, created = Delivery.objects.get_or_create(
                number=wz_number,
                defaults={
                    'provider': Provider.objects.get(shortcut=provider),
                    'date': datetime.date(int(date[2]), int(date[1]), int(date[0])),
                    'car_number': car_number[:16] if car_number else '',
                    'telephone': phone.replace(' ', '') if phone else '',
                }
            )

            if not created:
                errors.append(f'Delivery with number {wz_number} already exists.<br>')
                return render(request, "warehouse/load_wz_result.html", {
                    "results": result,
                    "errors": errors,
                    "delivery": delivery
                })

            for p in palletes_list:
                try:
                    palette = Palette.objects.get(name=f'{p.split(";")[0]} {p.split(";")[1]}')
                except Palette.DoesNotExist:
                    palette = Palette.objects.create(name=f'{p.split(";")[0]} {p.split(";")[1]}')

                DeliveryPalette.objects.create(
                    delivery=delivery,
                    palette=palette,
                    quantity=int(p.split(';')[2])
                )

        except Provider.DoesNotExist:
            errors.append(f'Provider {provider} does not exist.')
            return render(request, "warehouse/load_wz_result.html", {
                "results": result,
                "errors": errors,
                "delivery": None
            })
        except Exception as e:
            errors.append(f'Error creating delivery: {str(e)}')
            return render(request, "warehouse/load_wz_result.html", {
                "results": result,
                "errors": errors,
                "delivery": None
            })

        wrong_orders = []
        year_orders = {}

        for o in orders:
            print(o, "$$$")
            try:
                order_num_split, year_num_split = o[0].split('/')
                if len(year_num_split) == 2:
                    year_num_split = '20' + year_num_split

                year_orders.setdefault(year_num_split, []).append(int(order_num_split))
            except Exception:
                errors.append(f'Error creating item: {o}')
                wrong_orders.append(o)

        for key in year_orders:
            nums = get_rows_numbers2(year_orders[key], int(key), delivery.provider)
            load_orders(int(key), row_list=nums, preview_only=False)

        for wrong_order in wrong_orders:
            if wrong_order in orders:
                orders.remove(wrong_order)

        try:
            for item in orders:
                try:
                    order = Order.objects.get(order_id=item[0], provider=delivery.provider)
                    delivery_item = DeliveryItem.objects.create(
                        delivery=delivery,
                        order=order,
                        quantity=int(str(item[3]).replace(' ', '').replace(',', '')),
                        palettes_quantity=item[4] if len(item) > 4 else ''
                    )
                    result.append(f'{delivery_item} created')
                except Order.DoesNotExist:
                    errors.append(f'Order {item[0]} does not exist.')
                except Exception as e:
                    errors.append(f'Error creating delivery item {item}: {e}')
        except Exception as e:
            errors.append(f'General item creation error: {e}')

        return render(request, "warehouse/load_wz_result.html", {
            "results": result,
            "errors": errors,
            "delivery": delivery
        })


class OrderListView(PermissionRequiredMixin, View):
    permission_required = 'warehouse.view_order'
    login_url = reverse_lazy('login')

    def get(self, request):
        visit_counter(request.user, 'warehouse:orders')
        sort_by = request.GET.get('sort', 'order_date')
        order_direction = request.GET.get('dir', 'asc')
        manual = request.GET.get('manual')
        # all_orders = request.GET.get('all')
        customer = request.GET.get('customer')
        providers = Provider.objects.all()
        provider = request.GET.get('provider')
        years = [str(y) for y in range(2022, datetime.date.today().year + 1)]
        year = request.GET.get('year')
        status = request.GET.get('status')

        if order_direction == 'desc':
            sort_by = f'-{sort_by}'
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

        # if all_orders:
        #     orders = Order.objects.all().order_by(sort_by)
        # else:
        #     orders = Order.objects.filter(delivered=True, finished=False).order_by(sort_by)

        if any((customer, provider, year, status)):
            orders = Order.objects.all()

            if customer:
                customers = Buyer.objects.filter(name__icontains=customer)
                orders = orders.filter(customer__in=customers).order_by(sort_by)

            if provider:
                cardboard_providers = Provider.objects.filter(name__icontains=provider)
                orders = orders.filter(provider__in=cardboard_providers).order_by(sort_by)

            if year:
                start = datetime.date(int(year), 1, 1)
                end = datetime.date(int(year), 12, 31)
                orders = orders.filter(order_date__lte=end, order_date__gte=start).order_by(sort_by)

            if status:
                print(status)
                if status == "finished":
                    orders = orders.filter(finished=True).order_by(sort_by)
                elif status == "delivered":
                    orders = orders.filter(delivered=True).order_by(sort_by)
                else:
                    orders = orders.filter(delivered=False, finished=False).order_by(sort_by)

        else:
            orders = Order.objects.filter(delivered=True, finished=False).order_by(sort_by)


        orders_num = len(list(orders))
        return render(request, 'warehouse/order_list.html', locals())


class OrderDetailView(PermissionRequiredMixin, View):
    permission_required = 'warehouse.view_order'
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
        order = (
            Order.objects
            .select_related("customer", "provider", "product", "bom")
            .get(id=order_id)
        )

        stock_types = StockType.objects.filter(
            stock_type__in=["material", "product", "special"]
        ).order_by("stock_type", "unit")

        warehouses = Warehouse.objects.all()

        settlements = (
            OrderSettlement.objects
            .filter(order=order)
            .select_related("material", "material__stock", "material__warehouse")
        )

        warehouse_stocks_history = (
            WarehouseStockHistory.objects
            .filter(order_settlement__in=settlements)
            .select_related(
                "warehouse_stock",
                "warehouse_stock__stock",
                "warehouse_stock__warehouse",
                "order_settlement",
            )
        )

        sales = (
            ProductSell3.objects
            .filter(order=order)
            .select_related("customer", "product", "stock", "warehouse_stock")
        )

        items = (
            DeliveryItem.objects
            .filter(order=order)
            .select_related("delivery", "stock")
        )

        stock_supplies = (
            StockSupply.objects
            .filter(delivery_item__in=items)
            .select_related("stock_type", "delivery_item")
        )

        main_wh = Warehouse.objects.get(name="MAGAZYN GŁÓWNY")

        stock_names = list(stock_supplies.values_list("name", flat=True).distinct())

        stock_materials = (
            WarehouseStock.objects
            .select_related("stock", "stock__stock_type", "warehouse")
            .filter(
                warehouse=main_wh,
                stock__name__in=stock_names,
                quantity__gt=0,
            )
            .order_by("stock__name")
        )

        all_materials_in_warehouse = (
            WarehouseStock.objects
            .select_related("stock", "stock__stock_type", "warehouse")
            .filter(
                warehouse=main_wh,
                quantity__gt=0,
                stock__stock_type__stock_type="material",
            )
            .order_by("stock__name")
        )

        # NIE ŁADUJ CAŁEGO StockSupply.objects.all()
        stocks = StockSupply.objects.none()

        ld = None
        lq = None

        production_order = (
            ProductionOrder.objects
            .filter(id_number=f"{order.provider} {order.order_id}")
            .first()
        )

        if production_order:
            production_units = (
                ProductionUnit.objects
                .filter(production_order=production_order)
                .order_by("sequence")
            )

            last_unit = production_units.order_by("-sequence").first()
            if last_unit:
                lq = last_unit.quantity_end
                ld = last_unit.end.date()
        else:
            production_units = []

        cost = order.production_cost()
        other = order.other_costs()
        material_cost = order.material_cost()
        total_expenses = round(sum((material_cost, sum(cost), sum(other))), 2)
        earnings = order.total_sales()
        result = round(earnings - total_expenses, 2)

        products = [order.product] if order.product else []

        customers_sell = Buyer.objects.all().order_by("name")
        default_customer = order.customer

        warehouse_stocks_sell = (
            WarehouseStock.objects
            .select_related("stock", "warehouse")
            .filter(quantity__gt=0)
            .order_by("warehouse__name", "stock__name")
        )

        default_warehouse_stock = None
        quantity = None

        for h in warehouse_stocks_history:
            ws = h.warehouse_stock
            if ws and ws.warehouse.name == "MAGAZYN WYROBÓW GOTOWYCH":
                default_warehouse_stock = ws
                quantity = ws.quantity
                break

        today = datetime.date.today().isoformat()

        if not ld:
            for i in items:
                if i.delivery:
                    if not ld or ld < i.delivery.date:
                        ld = i.delivery.date

        return render(request, "warehouse/order_details.html", locals())


# to delete
# class AddShiftView(LoginRequiredMixin, View):
#     login_url = reverse_lazy('login')
#
#     def post(self, request, order_id):
#         order_from = get_object_or_404(Order, id=order_id)
#         form = OrderToOrderShiftForm(request.POST)
#
#         if form.is_valid():
#             shift: OrderToOrderShift = form.save(commit=False)
#             shift.order_from = order_from
#             # jeśli masz logikę wyliczania wartości, możesz tu ją uzupełnić
#             # shift.value = shift.quantity * (shift.order_to.product.price or 0)
#             shift.save()
#             messages.success(request, "Shift added.")
#             return redirect(request.META.get('HTTP_REFERER', '/'))
#         else:
#             messages.error(request, f"Cannot add shift: {form.errors.as_text()}")
#
#         return redirect(request.META.get('HTTP_REFERER', '/'))


class DeliveriesView(PermissionRequiredMixin, View):
    permission_required = 'warehouse.view_delivery'
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
        visit_counter(request.user, 'deliveries')
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


class DeliveryDetailView(PermissionRequiredMixin, View):
    permission_required = 'warehouse.view_delivery'
    login_url = reverse_lazy('login')

    def get(self, request, delivery_id):
        delivery = Delivery.objects.get(id=delivery_id)
        items = DeliveryItem.objects.filter(delivery=delivery).order_by('id')
        form = DeliveryItemForm(initial={'delivery': delivery})
        return render(request, 'warehouse/delivery_details.html', locals())


class DeliverySpecialDetailView(PermissionRequiredMixin, View):
    permission_required = 'warehouse.view_deliveryspecial'
    login_url = reverse_lazy('login')

    def get(self, request, delivery_id):
        delivery = DeliverySpecial.objects.get(id=delivery_id)
        items = DeliverySpecialItem.objects.filter(delivery=delivery)
        form = DeliverySpecialItemForm(initial={'delivery': delivery})
        return render(request, 'warehouse/delivery_special_details.html', locals())


class DeliveryEditView(PermissionRequiredMixin, View):
    permission_required = 'warehouse.edit_delivery'
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


class AddDeliveryItem(PermissionRequiredMixin, View):
    permission_required = 'warehouse.add_deliveryitem'
    login_url = reverse_lazy('login')

    def post(self, request):
        form = DeliveryItemForm(request.POST)
        delivery_id = form.data['delivery']
        if form.is_valid():
            form.save()
            return redirect('warehouse:delivery-detail-view', delivery_id=delivery_id)


class AddDeliverySpecialItem(PermissionRequiredMixin, View):
    permission_required = 'warehouse.add_deliveryspecialitem'
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


class AddDeliveryItemToWarehouse(PermissionRequiredMixin, View):
    permission_required = 'warehouse.add_deliveryitem'
    login_url = reverse_lazy('login')

    def get(self, request, delivery_id, item_id):
        item = DeliveryItem.objects.get(id=item_id)
        item.add_to_warehouse()

        return redirect("warehouse:delivery-detail-view", delivery_id=delivery_id)


class AddDeliveryToWarehouse(PermissionRequiredMixin, View):
    permission_required = 'warehouse.add_deliveryitem'
    login_url = reverse_lazy('login')

    def post(self, request, delivery_id):
        delivery = Delivery.objects.get(id=delivery_id)
        items = DeliveryItem.objects.filter(delivery=delivery)
        delivery.add_to_warehouse()

        return redirect("warehouse:delivery-detail-view", delivery_id=delivery_id)


class AddDeliverySpecialToWarehouse(PermissionRequiredMixin, View):
    permission_required = 'warehouse.add_deliveryitem'
    login_url = reverse_lazy('login')

    def post(self, request, delivery_id):
        delivery = DeliverySpecial.objects.get(id=delivery_id)
        items = DeliverySpecialItem.objects.filter(delivery=delivery)
        delivery.add_to_warehouse()

        return redirect("warehouse:delivery-special-detail-view", delivery_id=delivery_id)


class AddDeliverySpecialItemToWarehouse(PermissionRequiredMixin, View):
    permission_required = 'warehouse.add_deliveryitem'
    login_url = reverse_lazy('login')

    def get(self, request, delivery_id, item_id):
        item = DeliverySpecialItem.objects.get(id=item_id)
        item.add_to_warehouse()

        return redirect("warehouse:delivery-special-detail-view", delivery_id=delivery_id)


class WarehouseView(PermissionRequiredMixin, View):
    permission_required = 'warehouse.view_warehouse'
    login_url = reverse_lazy('login')

    def get(self, request, warehouse_id):
        all_stocks = request.GET.get('all_stocks')
        q = (request.GET.get('q') or '').strip()

        warehouse = Warehouse.objects.get(id=warehouse_id)

        stocks = WarehouseStock.objects.filter(warehouse=warehouse).select_related('stock')

        if not all_stocks:
            stocks = stocks.filter(quantity__gt=0)

        if q:
            stocks = stocks.filter(stock__name__icontains=q)

        stocks = stocks.order_by('stock__name')

        return render(request, 'warehouse/warehouse_details.html', locals())


class WarehouseListView(PermissionRequiredMixin, View):
    permission_required = 'warehouse.view_warehouse'
    login_url = reverse_lazy('login')

    def get(self, request):
        visit_counter(request.user, 'warehouse:warehouses')
        warehouses = Warehouse.objects.all()
        return render(request, 'warehouse/warehouse_list.html', locals())


class DeliveriesStatistics(PermissionRequiredMixin, View):
    permission_required = 'warehouse.add_delivery'
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
        visit_counter(request.user, 'deliveries-statistics')
        print(request.user)
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


class StockView(PermissionRequiredMixin, View):
    permission_required = 'warehouse.view_stock'
    login_url = reverse_lazy('login')

    def get(self, request, stock_id):
        stock = Stock.objects.get(id=stock_id)

        product = Product.objects.filter(name=stock.name).first()
        orders = Order.objects.filter(product=product) if product else Order.objects.none()
        product_supplies = StockSupply.objects.filter(name=stock.name)

        history = WarehouseStockHistory.objects.filter(warehouse_stock__stock=stock)

        return render(request, 'warehouse/stock-details.html', locals())


# toremove
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


class WarehouseStockHistoryDetailView(PermissionRequiredMixin, DetailView):
    permission_required = 'warehouse.view_warehousestockhistory'
    login_url = reverse_lazy('login')
    model = WarehouseStock
    template_name = "warehouse/warehouse_stock_history.html"
    context_object_name = "ws"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        history_qs = (
            WarehouseStockHistory.objects
            .filter(warehouse_stock=self.object)
            .select_related(
                "stock_supply",
                "order_settlement",
                "order_settlement__order",
                "assembly",
            )
            .order_by("-date", "-id")
        )

        ctx["history"] = history_qs
        return ctx


class WarehouseStockDetailView(PermissionRequiredMixin, DetailView):
    permission_required = 'warehouse.view_warehousestock'
    model = WarehouseStock
    template_name = "warehouse/warehouse-stock-details.html"
    context_object_name = "ws"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ws = self.object

        # Historia: wszystko co zmieniało ws.quantity
        history_qs = (
            WarehouseStockHistory.objects
            .filter(warehouse_stock=ws)
            .select_related(
                "stock_supply",
                "stock_supply__delivery_item",
                "stock_supply__delivery_item__delivery",
                "order_settlement",
                "order_settlement__order",
                "sell",
                "sell__customer",
            )
            .order_by("-date", "-id")
        )

        # szybkie linki/źródła
        order_ids = list(
            history_qs
            .filter(order_settlement__isnull=False)
            .values_list("order_settlement__order_id", flat=True)
            .distinct()
        )

        delivery_ids = list(
            history_qs
            .filter(stock_supply__delivery_item__delivery_id__isnull=False)
            .values_list("stock_supply__delivery_item__delivery_id", flat=True)
            .distinct()
        )

        ctx["history"] = history_qs
        ctx["order_ids"] = order_ids
        ctx["delivery_ids"] = delivery_ids

        # formularz FIFO (na górze)
        last_date = self.request.session.get("last_fifo_sell_date")

        ctx["fifo_sell_form"] = WarehouseStockFifoSellForm(
            initial={
                "date": last_date or datetime.date.today()
            }
        )

        return ctx

    def post(self, request, *args, **kwargs):
        print("[WS_DETAIL] HIT", request.method, request.path)
        """
        Obsługa sprzedaży FIFO bezpośrednio z widoku WarehouseStock.
        """
        self.object = self.get_object()
        ws = self.object

        form = WarehouseStockFifoSellForm(request.POST)
        if not form.is_valid():
            messages.error(request, f"Błędy formularza: {form.errors}")
            return redirect(request.path)

        cd = form.cleaned_data

        try:
            with transaction.atomic():
                ws_locked = WarehouseStock.objects.select_for_update().get(pk=ws.pk)

                qty = int(cd["quantity"])
                if ws_locked.quantity < qty:
                    raise ValidationError("Nie ma wystarczającej ilości w magazynie!")

                # ✅ produkt opcjonalny (dla materiału będzie None)
                resolved_product = getattr(ws_locked.stock, "product", None)

                sale = ProductSell3.objects.create(
                    product=resolved_product,  # może być None
                    stock=ws_locked.stock,  # ✅ zawsze
                    customer=cd.get("customer"),
                    customer_alter_name=(cd.get("customer_alter_name") or None),
                    warehouse_stock=ws_locked,
                    order=None,  # FIFO
                    quantity=qty,
                    price=cd["price"],
                    date=cd["date"],
                )

                ws_locked.fifo_sell(sale)
                attach_origin_orders_to_sell(sale)
                request.session["last_fifo_sell_date"] = str(cd["date"])

            messages.success(request, "Sprzedaż FIFO zapisana.")
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            # zostaw to — w razie błędu masz traceback w konsoli
            import logging
            logging.getLogger(__name__).exception("[WS_DETAIL FIFO SELL] ERROR")
            messages.error(request, f"Błąd sprzedaży: {e}")

        return redirect(request.path)


class LoadDeliveryToGSFile(PermissionRequiredMixin, View):
    permission_required = 'warehouse.add_delivery'
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


class SellProductList(PermissionRequiredMixin, View):
    permission_required = 'warehouse.add_productsell3'
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


class ProductSell3CreateView(PermissionRequiredMixin, CreateView):
    permission_required = 'warehouse.add_productsell3'
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
            sell.full_clean()
            sell.save()

            # ✅ FIFO sprzedaż (rozpisze na partie + zrobi historię + zmniejszy ws.quantity)
            ws.fifo_sell(sell)

        messages.success(self.request, "Sprzedaż zapisana (FIFO).")
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        print(form.errors)
        print(form.cleaned_data)
        return redirect(self.get_success_url())


class PaletteView(PermissionRequiredMixin, View):
    permission_required = 'warehouse.view_palette'
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


class AddOrdersManually(PermissionRequiredMixin, View):
    permission_required = 'warehouse.add_order'
    login_url = reverse_lazy('login')
    template_name = "warehouse/add_orders.html"

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

        if not form.is_valid():
            messages.error(request, 'Formularz zawiera błędy. Popraw je i spróbuj ponownie.')
            context = self.get_context_data(form=form)
            return render(request, 'warehouse/add_orders.html', context=context)

        source = (form.cleaned_data.get('source') or '').strip().lower()
        confirm_new_products = request.POST.get("confirm_new_products") == "1"

        try:
            if source == 'sheet':
                row = form.cleaned_data['sheet_row']
                year = form.cleaned_data['year']

                if not confirm_new_products:
                    preview = load_orders(
                        int(year),
                        row=int(row) - 1,
                        preview_only=True
                    )

                    if preview["new_products"]:
                        return render(request, 'warehouse/confirm_new_products.html', {
                            'form': form,
                            'new_products': preview["new_products"],
                            'source': 'sheet',
                            'sheet_row': row,
                            'year': year,
                        })

                final_result = load_orders(
                    int(year),
                    row=int(row) - 1,
                    preview_only=False
                )

                messages.success(
                    request,
                    f'Pomyślnie załadowano zamówienia z wiersza {row}. {final_result["result"]}'
                )
                return redirect('warehouse:add-orders')

            elif source == 'provider':
                provider = form.cleaned_data['provider']
                order_no = form.cleaned_data['provider_order_number']
                year = form.cleaned_data['year']

                rows = get_rows_numbers2([int(order_no)], int(year), provider)

                if not confirm_new_products:
                    preview = load_orders(
                        int(year),
                        row_list=rows,
                        preview_only=True
                    )

                    if preview["new_products"]:
                        return render(request, 'warehouse/confirm_new_products.html', {
                            'form': form,
                            'new_products': preview["new_products"],
                            'source': 'provider',
                            'provider_id': provider.id,
                            'provider_order_number': order_no,
                            'year': year,
                        })

                final_result = load_orders(
                    int(year),
                    row_list=rows,
                    preview_only=False
                )

                messages.success(
                    request,
                    f'Pomyślnie załadowano zamówienie {order_no} od dostawcy {provider}. {final_result["result"]}'
                )
                return redirect('warehouse:add-orders')

            messages.error(request, f'Nieobsługiwane źródło importu: {source}')
            context = self.get_context_data(form=form)
            return render(request, 'warehouse/add_orders.html', context=context)

        except Exception as e:
            messages.error(
                request,
                f'Wystąpił błąd podczas importu zamówień: {e}'
            )
            context = self.get_context_data(form=form)
            return render(request, 'warehouse/add_orders.html', context=context)


def add_product_sell3(request):
    user = request.user
    if user.has_perm('warehouse.add_productsell3'):
        if request.method != "POST":
            return redirect(request.META.get("HTTP_REFERER", "/"))

        try:
            with transaction.atomic():
                warehouse_stock = WarehouseStock.objects.select_for_update().get(
                    id=int(request.POST.get("warehouse_stock"))
                )

                # klient
                customer_id = request.POST.get("customer")
                customer = Buyer.objects.get(id=int(customer_id)) if customer_id else None
                customer_alter_name = (request.POST.get("customer_alter_name") or "").strip() or None
                if not customer and not customer_alter_name:
                    raise ValidationError("Podaj klienta lub wpisz nazwę ręcznie.")

                # order opcjonalny
                order_id = request.POST.get("order")
                order = Order.objects.get(id=int(order_id)) if order_id else None

                quantity = int(request.POST.get("quantity_sell"))

                # ...
                date_raw = request.POST.get("date_sell")  # string z inputa
                date = parse_date(date_raw)  # obsługuje 'YYYY-MM-DD'

                # jeśli czasem wysyłasz 'dd-mm-YYYY' (bo tak masz w UI), dodaj fallback:
                if date is None and date_raw:
                    try:
                        date = datetime.datetime.strptime(date_raw, "%d-%m-%Y").date()
                    except ValueError:
                        date = None

                if date is None:
                    raise ValidationError(f"Niepoprawna data sprzedaży: {date_raw}")
                price = request.POST.get("price_sell")

                if quantity <= 0:
                    raise ValidationError("Ilość musi być większa od zera.")
                if warehouse_stock.quantity < quantity:
                    raise ValidationError("Nie ma wystarczającej ilości w magazynie!")

                # ✅ PRODUKT: jeśli formularz podał product -> bierzemy z POST (OrderDetail)
                product_id = request.POST.get("product")
                if product_id:
                    product = Product.objects.get(id=int(product_id))
                else:
                    # fallback: jeśli Stock ma przypięty Product
                    product = getattr(warehouse_stock.stock, "product", None)

                # opcjonalna spójność: jeśli stock ma przypięty product, a user wybrał inny -> błąd
                stock_prod = getattr(warehouse_stock.stock, "product", None)
                if stock_prod and product and stock_prod.id != product.id:
                    raise ValidationError("Wybrany produkt nie zgadza się z produktem powiązanym ze stockiem.")

                sale = ProductSell3.objects.create(
                    product=product,                      # ✅ dla OrderDetail będzie ustawiony
                    stock=warehouse_stock.stock,           # ✅ zawsze
                    customer=customer,
                    customer_alter_name=customer_alter_name,
                    warehouse_stock=warehouse_stock,
                    order=order,
                    quantity=quantity,
                    price=price,
                    date=date,
                )

                # rozchód
                if sale.order_id:
                    warehouse_stock.sell_from_order(sale)
                    attach_origin_orders_to_sell(sale)     # ✅ też warto dopiąć po order-sellu
                else:
                    warehouse_stock.fifo_sell(sale)
                    attach_origin_orders_to_sell(sale)

                # aktualizacja ceny produktu tylko jeśli produkt istnieje
                if sale.product_id:
                    sale.product.price = price
                    sale.product.save(update_fields=["price"])

            messages.success(request, "Sprzedaż zapisana.")

        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            logger.exception("[ADD_SELL] ERROR")
            messages.error(request, f"Błąd zapisu sprzedaży: {e}")

        return redirect(request.META.get("HTTP_REFERER", "/"))


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
            customer = Buyer.objects.get(name=data[18].upper().strip())
            flute = get_flute(data[19].upper().strip())
            dimensions = f'{data[23].strip()}'
            extra = data[24].upper().strip()
            # product_name = build_product_name(customer.name, flute, dimensions, extra)

            product = safe_get_or_create_product(customer.name, flute, dimensions, extra)
            print("dopisywanie")
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


class CreateOrderFromBOMView(PermissionRequiredMixin, View):
    """
    Tworzy Order i automatycznie podpina:
      - order.bom = BOM
      - order.product = BOM.product
    """
    permission_required = 'warehouse.add_order'

    def get(self, request, bom_id: int):

        from warehouse.services.orders import next_free_order_id_for_bom
        bom = get_object_or_404(BOM, pk=bom_id)
        data = bom.product.name.split("|")

        customer = get_object_or_404(Buyer, name=data[0].strip())
        provider = get_object_or_404(Provider, name="PAKER")
        order_id = next_free_order_id_for_bom(bom=bom, date=datetime.date.today())

        # sensowne podpowiedzi
        initial = {
            "price": int(bom.product.price) if bom.product.price else 0,
            "name": data[2].strip(),
            "dimensions": "0x0",
            "provider": provider,
            "customer": customer,
            "order_id": order_id,
            "delivered": True
        }

        form = OrderFromBOMForm(initial=initial)
        return render(request, "warehouse/bom_create_order.html", {"bom": bom, "form": form})

    def post(self, request, bom_id: int):
        bom = get_object_or_404(BOM, pk=bom_id)
        form = OrderFromBOMForm(request.POST)

        if not form.is_valid():
            return render(request, "warehouse/bom_create_order.html", {"bom": bom, "form": form})

        try:
            with transaction.atomic():
                order: Order = form.save(commit=False)

                # auto-powiązania
                order.bom = bom
                order.product = bom.product

                # pola wymagane / spójność
                od = order.order_date or datetime.date.today()
                order.order_year = str(od.year)

                # customer_date jest wymagane w modelu
                if not order.customer_date:
                    order.customer_date = od

                order.full_clean()
                order.save()

            messages.success(request, f"Utworzono zamówienie {order.provider} {order.order_id} z BOM: {bom}.")
            return redirect("warehouse:order-detail-view", order_id=order.id)

        except Exception as e:
            messages.error(request, f"Nie udało się utworzyć zamówienia: {e}")
            return render(request, "warehouse/bom_create_order.html", {"bom": bom, "form": form})


class BOMListView(PermissionRequiredMixin, ListView):
    permission_required = 'warehouse.view_bom'
    template_name = "warehouse/bom_list.html"
    model = BOM
    context_object_name = "boms"
    paginate_by = 50

    def get_queryset(self):
        qs = (
            BOM.objects
            .select_related("product")
            .order_by("-id")
        )
        return qs


class BOMDetailView(PermissionRequiredMixin, DetailView):
    permission_required = 'warehouse.view_bom'
    model = BOM
    template_name = "warehouse/bom_detail.html"
    context_object_name = "bom"

    def get_queryset(self):
        return (
            BOM.objects
            .select_related("product")
            .prefetch_related(
                "parts__part",
                "parts__part__stock_type",
                Prefetch(
                    "orders",
                    queryset=Order.objects.select_related("customer", "provider", "product").order_by("-order_date", "-id")
                )
            )
        )


class ProductPackagingListView(PermissionRequiredMixin, View):
    permission_required = 'warehouse.view_productpackaging'
    login_url = reverse_lazy("login")

    def get(self, request):
        q = (request.GET.get("q") or "").strip()

        products = Product.objects.all().order_by("name")
        if q:
            products = products.filter(name__icontains=q)

        # ważne: OneToOne related_name="packaging"
        products = products.select_related("packaging")

        palettes = Palette.objects.all().order_by("name")
        default_palette = Palette.objects.filter(name="EPAL 1200x800").first()
        print(default_palette)

        return render(request, "warehouse/product_packaging_list.html", {
            "products": products,
            "palettes": palettes,
            "q": q,
            "csrf_token": get_token(request),
            "default_palette_id": default_palette.id if default_palette else None,
        })


@method_decorator(require_POST, name="dispatch")
class ProductPackagingUpsertAjaxView(PermissionRequiredMixin, View):
    permission_required = 'warehouse.add_productpackaging'
    login_url = reverse_lazy("login")

    def post(self, request):
        try:
            product_id = int(request.POST.get("product_id"))
            palette_id_raw = request.POST.get("palette_id")  # może być puste
            columns = int(request.POST.get("columns") or 0)
            layers = int(request.POST.get("layers") or 0)
            qty_per_pack = int(request.POST.get("qty_per_pack") or 0)
            additional_info = request.POST.get("additional_info") or ""
        except (TypeError, ValueError):
            return JsonResponse({"success": False, "error": "Nieprawidłowe dane wejściowe."}, status=400)

        product = get_object_or_404(Product, id=product_id)

        palette = None
        if palette_id_raw:
            try:
                palette = Palette.objects.get(id=int(palette_id_raw))
            except (Palette.DoesNotExist, ValueError):
                return JsonResponse({"success": False, "error": "Nieprawidłowa paleta."}, status=400)

        packaging, _created = ProductPackaging.objects.get_or_create(product=product)

        packaging.palette = palette
        packaging.columns = columns
        packaging.layers = layers
        packaging.qty_per_pack = qty_per_pack
        packaging.additional_info = additional_info

        try:
            packaging.full_clean()
            packaging.save()  # qty_per_pallet policzy się w save()
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)

        return JsonResponse({
            "success": True,
            "product_id": product.id,
            "qty_per_pallet": packaging.qty_per_pallet,
            "palette": str(packaging.palette) if packaging.palette else "",
            "columns": packaging.columns,
            "layers": packaging.layers,
            "qty_per_pack": packaging.qty_per_pack,
            "aadditional_info": packaging.additional_info,
        })


def undo_order_settlement(request, settlement_id):
    if request.user.has_perm('warehouse.add_ordersettlement'):
        if request.method != "POST":
            return redirect(request.META.get("HTTP_REFERER", "/"))

        if not _check_undo_password(request):
            messages.error(request, "Nieprawidłowe hasło do cofania operacji.")
            return redirect(request.META.get("HTTP_REFERER", "/"))

        try:
            with transaction.atomic():
                settlement = OrderSettlement.objects.select_for_update().get(pk=settlement_id)

                touched_ws_ids = set()
                settlement_date = settlement.settlement_date

                result_rows = list(
                    StockSupplySettlement.objects
                    .select_for_update()
                    .filter(settlement=settlement, as_result=True)
                    .select_related("stock_supply")
                    .order_by("id")
                )

                for row in result_rows:
                    supply = row.stock_supply

                    sold_qty = (
                        StockSupplySell.objects
                        .filter(stock_supply=supply)
                        .aggregate(s=Sum("quantity"))["s"] or 0
                    )
                    if sold_qty > 0:
                        raise ValidationError(
                            f"Nie można cofnąć rozliczenia. Partia '{supply.name}' została już sprzedana ({sold_qty})."
                        )

                hist_rows = list(
                    WarehouseStockHistory.objects
                    .select_for_update()
                    .filter(order_settlement=settlement)
                    .order_by("date", "id")
                )

                for h in hist_rows:
                    touched_ws_ids.add(h.warehouse_stock_id)

                WarehouseStockHistory.objects.filter(order_settlement=settlement).delete()

                for row in result_rows:
                    supply = row.stock_supply
                    row.delete()
                    supply.delete()

                material_rows = list(
                    StockSupplySettlement.objects
                    .select_for_update()
                    .filter(settlement=settlement, as_result=False)
                    .select_related("stock_supply")
                )

                touched_supplies = []
                for row in material_rows:
                    if row.stock_supply_id:
                        touched_supplies.append(row.stock_supply)
                    row.delete()

                for supply in touched_supplies:
                    supply.refresh_used_flag()

                settlement.delete()

                for ws_id in touched_ws_ids:
                    ws = WarehouseStock.objects.select_for_update().get(pk=ws_id)
                    rebuild_ws_history_from_date(ws=ws, from_date=settlement_date)

            messages.success(request, "Rozliczenie zostało cofnięte.")
        except Exception as e:
            messages.error(request, f"Błąd cofania rozliczenia: {e}")

        return redirect(request.META.get("HTTP_REFERER", "/"))


def undo_product_sell(request, sell_id):
    if request.user.has_perm('warehouse.delete_productsell3'):
        if request.method != "POST":
            return redirect(request.META.get("HTTP_REFERER", "/"))

        if not _check_undo_password(request):
            messages.error(request, "Nieprawidłowe hasło do cofania operacji.")
            return redirect(request.META.get("HTTP_REFERER", "/"))

        try:
            with transaction.atomic():
                sell = ProductSell3.objects.select_for_update().get(pk=sell_id)

                if not sell.warehouse_stock_id:
                    raise ValueError("Sprzedaż nie ma przypisanego warehouse_stock.")

                qty = int(sell.quantity or 0)
                if qty <= 0:
                    raise ValueError("Sprzedaż ma nieprawidłową ilość.")

                sell_date = sell.date
                ws = WarehouseStock.objects.select_for_update().get(pk=sell.warehouse_stock_id)

                WarehouseStockHistory.objects.filter(sell=sell).delete()

                supply_rows = list(
                    StockSupplySell.objects
                    .select_for_update()
                    .filter(sell=sell)
                    .select_related("stock_supply")
                )

                touched_supplies = []
                for row in supply_rows:
                    if row.stock_supply_id:
                        touched_supplies.append(row.stock_supply)
                    row.delete()

                seen_ids = set()
                for supply in touched_supplies:
                    if supply.id in seen_ids:
                        continue
                    seen_ids.add(supply.id)
                    supply.refresh_used_flag()

                sell.order_parts.all().delete()
                sell.delete()

                rebuild_ws_history_from_date(ws=ws, from_date=sell_date)

            messages.success(request, "Sprzedaż została cofnięta.")
        except Exception as e:
            messages.error(request, f"Błąd cofania sprzedaży: {e}")

        return redirect(request.META.get("HTTP_REFERER", "/"))


def refresh_warehouses_values(request):
    # if request.method != "POST":
    #     return redirect(request.META.get("HTTP_REFERER", "/"))
    warehouses = Warehouse.objects.all()
    for w in warehouses:
        w.count_warehouse_value()

    return redirect(request.META.get("HTTP_REFERER", "/"))

from decimal import Decimal, InvalidOperation

from decimal import Decimal, InvalidOperation

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse, reverse_lazy
from django.utils.dateparse import parse_date
from django.views import View

from production.models import ProductionOrder, ProductionUnit
from warehouse.models import Order, Product
from warehousemanager.models import LocalSetting


class OrderProfitabilityListView(LoginRequiredMixin, View):
    login_url = reverse_lazy("login")
    template_name = "warehouse/order_profitability_list.html"

    @staticmethod
    def get_setting_decimal(name, default):
        setting = LocalSetting.objects.filter(name=name).first()

        if not setting:
            return Decimal(str(default))

        try:
            return Decimal(str(setting.value).replace(",", "."))
        except (InvalidOperation, TypeError, ValueError):
            return Decimal(str(default))

    def get(self, request):
        from warehousemanager.models import Person

        production_hourly_rate = self.get_setting_decimal(
            "production_work_hour_value",
            "57.00",
        )

        fully_loaded_hourly_rate = self.get_setting_decimal(
            "work_hour_value",
            "192.00",
        )

        if fully_loaded_hourly_rate < production_hourly_rate:
            fully_loaded_hourly_rate = production_hourly_rate

        persons = Person.objects.all().order_by(
            "first_name",
            "last_name",
        )

        date_from = request.GET.get("date_from", "")
        date_to = request.GET.get("date_to", "")
        customer = request.GET.get("customer", "").strip()
        person_id = request.GET.get("person")
        product_id = request.GET.get("product")
        group_by = request.GET.get("group_by", "orders")

        if group_by not in {"orders", "products"}:
            group_by = "orders"

        selected_person_id = None

        if person_id:
            try:
                selected_person_id = int(person_id)
            except (TypeError, ValueError):
                selected_person_id = None

        selected_product = None
        selected_product_id = None

        if product_id:
            try:
                selected_product_id = int(product_id)
                selected_product = Product.objects.filter(
                    pk=selected_product_id
                ).first()

                if not selected_product:
                    selected_product_id = None

            except (TypeError, ValueError):
                selected_product_id = None
                selected_product = None

        has_filters = any([
            selected_person_id,
            customer,
            date_from,
            date_to,
            selected_product_id,
        ])

        return render(request, self.template_name, {
            "persons": persons,
            "person_id": selected_person_id,
            "customer": customer,
            "date_from": date_from,
            "date_to": date_to,
            "group_by": group_by,
            "product_id": selected_product_id,
            "selected_product": selected_product,
            "production_hourly_rate": production_hourly_rate,
            "fully_loaded_hourly_rate": fully_loaded_hourly_rate,
            "has_filters": has_filters,
        })


class OrderProfitabilityDataView(LoginRequiredMixin, View):
    login_url = reverse_lazy("login")
    PAGE_SIZE = 50

    @staticmethod
    def get_setting_decimal(name, default):
        setting = LocalSetting.objects.filter(name=name).first()

        if not setting:
            return Decimal(str(default))

        try:
            return Decimal(str(setting.value).replace(",", "."))
        except (InvalidOperation, TypeError, ValueError):
            return Decimal(str(default))

    def get_rates(self):
        production_hourly_rate = self.get_setting_decimal(
            "production_work_hour_value",
            "57.00",
        )

        fully_loaded_hourly_rate = self.get_setting_decimal(
            "work_hour_value",
            "192.00",
        )

        if fully_loaded_hourly_rate < production_hourly_rate:
            fully_loaded_hourly_rate = production_hourly_rate

        return production_hourly_rate, fully_loaded_hourly_rate

    def get_base_queryset(self, request):
        from warehousemanager.models import Person

        person_id = request.GET.get("person")
        customer = request.GET.get("customer", "").strip()
        product_id = request.GET.get("product")

        date_from = parse_date(
            request.GET.get("date_from") or ""
        )

        date_to = parse_date(
            request.GET.get("date_to") or ""
        )

        qs = (
            Order.objects
            .select_related(
                "provider",
                "customer",
                "product",
            )
            .order_by("-order_date", "-id")
        )

        if person_id:
            try:
                person_id = int(person_id)
            except (TypeError, ValueError):
                return Order.objects.none()

            person = Person.objects.filter(
                pk=person_id
            ).first()

            if not person:
                return Order.objects.none()

            qs = (
                Order.produced_by_person(person)
                .select_related(
                    "provider",
                    "customer",
                    "product",
                )
                .order_by("-order_date", "-id")
            )

        if customer:
            qs = qs.filter(
                customer__name__icontains=customer
            )

        if product_id:
            try:
                product_id = int(product_id)
            except (TypeError, ValueError):
                return Order.objects.none()

            qs = qs.filter(
                product_id=product_id
            )

        if date_from:
            qs = qs.filter(
                order_date__gte=date_from
            )

        if date_to:
            qs = qs.filter(
                order_date__lte=date_to
            )

        return qs

    def get_production_order(self, order):
        return (
            ProductionOrder.objects
            .filter(
                id_number=f"{order.provider} {order.order_id}"
            )
            .first()
        )

    def order_has_production_time(self, order):
        production_order = self.get_production_order(order)

        if not production_order:
            return False

        return ProductionUnit.objects.filter(
            production_order=production_order,
            start__isnull=False,
            end__isnull=False,
        ).exists()

    def build_order_row(
        self,
        order,
        production_hourly_rate,
        fully_loaded_hourly_rate,
    ):
        settled_qty = int(
            order.settled_quantity() or 0
        )

        sold_qty = int(
            order.sold_quantity() or 0
        )

        if settled_qty <= 0:
            return None

        if sold_qty <= 0:
            return None

        if not order.product_id:
            return None

        if not self.order_has_production_time(order):
            return None

        material_cost = Decimal(
            str(order.material_cost() or 0)
        )

        work_hours = Decimal(
            str(order.production_work_hours() or 0)
        )

        sales = Decimal(
            str(order.real_sales_value() or 0)
        )

        if work_hours <= 0:
            return None

        labor_cost = (
            work_hours
            * production_hourly_rate
        )

        production_cost = (
            material_cost
            + labor_cost
        )

        production_result = (
            sales
            - production_cost
        )

        additional_cost = (
            fully_loaded_hourly_rate
            - production_hourly_rate
        ) * work_hours

        fully_loaded_cost = (
            production_cost
            + additional_cost
        )

        fully_loaded_result = (
            sales
            - fully_loaded_cost
        )

        status = order.sales_profitability_status()

        return {
            "row_type": "order",
            "id": order.id,
            "product_id": order.product_id,
            "order": f"{order.provider} {order.order_id}",
            "order_url": reverse(
                "warehouse:order-detail-view",
                args=[order.id],
            ),
            "order_date": (
                order.order_date.strftime("%d.%m.%Y")
                if order.order_date
                else ""
            ),
            "customer": (
                str(order.customer)
                if order.customer
                else ""
            ),
            "product": (
                order.product.name
                if order.product
                else ""
            ),
            "orders_count": 1,
            "settled_qty": settled_qty,
            "sold_qty": sold_qty,
            "material_cost": float(material_cost),
            "work_hours": float(work_hours),
            "labor_cost": float(labor_cost),
            "sales": float(sales),
            "production_result": float(production_result),
            "additional_cost": float(additional_cost),
            "fully_loaded_cost": float(fully_loaded_cost),
            "fully_loaded_result": float(fully_loaded_result),
            "status": status,
            "is_production_profit": production_result >= 0,
            "is_fully_loaded_profit": fully_loaded_result >= 0,
        }

    def build_order_rows(self, request):
        (
            production_hourly_rate,
            fully_loaded_hourly_rate,
        ) = self.get_rates()

        rows = []

        for order in self.get_base_queryset(request):
            row = self.build_order_row(
                order=order,
                production_hourly_rate=production_hourly_rate,
                fully_loaded_hourly_rate=fully_loaded_hourly_rate,
            )

            if row:
                rows.append(row)

        return rows

    def aggregate_product_rows(self, order_rows):
        products = {}

        for row in order_rows:
            product_id = row.get("product_id")

            if not product_id:
                continue

            if product_id not in products:
                products[product_id] = {
                    "row_type": "product",
                    "product_id": product_id,
                    "product": row["product"],
                    "customers": set(),
                    "orders_count": 0,
                    "settled_qty": 0,
                    "sold_qty": 0,
                    "material_cost": Decimal("0.00"),
                    "work_hours": Decimal("0.00"),
                    "labor_cost": Decimal("0.00"),
                    "sales": Decimal("0.00"),
                    "production_result": Decimal("0.00"),
                    "additional_cost": Decimal("0.00"),
                    "fully_loaded_cost": Decimal("0.00"),
                    "fully_loaded_result": Decimal("0.00"),
                }

            product = products[product_id]

            if row["customer"]:
                product["customers"].add(
                    row["customer"]
                )

            product["orders_count"] += 1
            product["settled_qty"] += row["settled_qty"]
            product["sold_qty"] += row["sold_qty"]

            for field in (
                "material_cost",
                "work_hours",
                "labor_cost",
                "sales",
                "production_result",
                "additional_cost",
                "fully_loaded_cost",
                "fully_loaded_result",
            ):
                product[field] += Decimal(
                    str(row[field])
                )

        result = []

        decimal_fields = (
            "material_cost",
            "work_hours",
            "labor_cost",
            "sales",
            "production_result",
            "additional_cost",
            "fully_loaded_cost",
            "fully_loaded_result",
        )

        for product in products.values():
            product["customer"] = ", ".join(
                sorted(product.pop("customers"))
            )

            product["is_production_profit"] = (
                product["production_result"] >= 0
            )

            product["is_fully_loaded_profit"] = (
                product["fully_loaded_result"] >= 0
            )

            for field in decimal_fields:
                product[field] = float(
                    product[field]
                )

            result.append(product)

        return sorted(
            result,
            key=lambda item: (
                item["product"] or ""
            ).lower(),
        )

    def get(self, request):
        try:
            page = max(
                int(request.GET.get("page", 1)),
                1,
            )
        except (TypeError, ValueError):
            page = 1

        group_by = request.GET.get(
            "group_by",
            "orders",
        )

        if group_by not in {"orders", "products"}:
            group_by = "orders"

        order_rows = self.build_order_rows(request)

        if group_by == "products":
            all_rows = self.aggregate_product_rows(
                order_rows
            )
        else:
            all_rows = order_rows

        paginator = Paginator(
            all_rows,
            self.PAGE_SIZE,
        )

        page_obj = paginator.get_page(page)

        (
            production_hourly_rate,
            fully_loaded_hourly_rate,
        ) = self.get_rates()

        return JsonResponse({
            "rows": list(page_obj.object_list),
            "page": page_obj.number,
            "has_next": page_obj.has_next(),
            "has_previous": page_obj.has_previous(),
            "num_pages": paginator.num_pages,
            "total_rows": paginator.count,
            "group_by": group_by,
            "production_hourly_rate": float(
                production_hourly_rate
            ),
            "fully_loaded_hourly_rate": float(
                fully_loaded_hourly_rate
            ),
        })


from django.contrib.auth import get_user_model, login
class ShipmentUnitConfirmUserView(LoginRequiredMixin, View):
    login_url = reverse_lazy("login")
    template_name = "warehouse/shipment_unit_confirm_user.html"

    def get(self, request, order_id):
        order = get_object_or_404(
            Order.objects.select_related("product"),
            id=order_id,
        )
        user = request.user

        return render(request, self.template_name, {
            "order": order,
            "user": user
        })

    def post(self, request, order_id):
        from warehousemanager.models import Person

        order = get_object_or_404(
            Order.objects.select_related("product"),
            id=order_id,
        )

        username = (request.POST.get("username") or "").strip()
        pin = (request.POST.get("pin") or "").strip()

        print(username, pin)

        User = get_user_model()

        try:
            user = User.objects.get(
                username=username,
                is_active=True,
            )

            print(user)

            person = Person.objects.get(
                user=user,
                # job_end__isnull=True,
            )
            print(person)

        except (User.DoesNotExist, Person.DoesNotExist):
            return render(request, self.template_name, {
                "order": order,
                "username": username,
                "error": "Nieprawidłowa nazwa użytkownika lub PIN.",
            })

        print(person.check_pin(pin))

        if not person.pin or not person.check_pin(pin):
            return render(request, self.template_name, {
                "order": order,
                "username": username,
                "error": "Nieprawidłowa nazwa użytkownika lub PIN.",
            })

        login(
            request,
            user,
            backend="django.contrib.auth.backends.ModelBackend",
        )

        return redirect(
            "warehouse:shipment-unit-create",
            order_id=order.id,
        )


class ShipmentUnitCreateView(LoginRequiredMixin, View):
    login_url = reverse_lazy("login")
    template_name = "warehouse/shipment_unit_create.html"

    def get_shipment_units(self, order):
        shipped_items = ShipmentItem.objects.filter(
            shipment_unit_id=OuterRef("pk"),
            shipment__status=Shipment.STATUS_CONFIRMED,
        )

        loading_items = ShipmentItem.objects.filter(
            shipment_unit_id=OuterRef("pk"),
            shipment__status=Shipment.STATUS_DRAFT,
        )

        return (
            ShipmentUnit.objects
            .filter(order=order)
            .select_related(
                "product",
                "palette",
                "created_by",
            )
            .annotate(
                is_shipped=Exists(shipped_items),
                is_loading=Exists(loading_items),
            )
            .order_by("-created", "-id")
        )

    def get_context(self, order, **kwargs):
        packaging = (
            ProductPackaging.objects
            .select_related("palette")
            .filter(product=order.product)
            .first()
        )
        shipment_unit_history = (
            ShipmentUnitHistory.objects
            .filter(order=order)
            .select_related(
                "shipment_unit",
                "product",
                "palette",
                "changed_by",
            )
            .order_by("-changed_at", "-id")
        )

        context = {
            "order": order,
            "packaging": packaging,
            "palettes": Palette.objects.all().order_by("name"),
            "default_palette": packaging.palette if packaging else None,
            "shipment_units": self.get_shipment_units(order),
            "shipment_unit_history": shipment_unit_history,
        }

        context.update(kwargs)

        return context

    def get(self, request, order_id):
        order = get_object_or_404(
            Order.objects.select_related("product"),
            id=order_id,
        )

        return render(
            request,
            self.template_name,
            self.get_context(order),
        )

    def post(self, request, order_id):
        order = get_object_or_404(
            Order.objects.select_related("product"),
            id=order_id,
        )

        quantity_raw = request.POST.get("quantity")
        units_count_raw = request.POST.get("units_count", "1")
        palette_id = request.POST.get("palette")

        try:
            quantity = int(quantity_raw)
        except (TypeError, ValueError):
            quantity = 0

        try:
            units_count = int(units_count_raw)
        except (TypeError, ValueError):
            units_count = 0

        palette = None

        if palette_id:
            palette = Palette.objects.filter(id=palette_id).first()

            if not palette:
                return render(
                    request,
                    self.template_name,
                    self.get_context(
                        order,
                        quantity=quantity_raw,
                        units_count=units_count_raw,
                        selected_palette_id=palette_id,
                        error="Wybrana paleta nie istnieje.",
                    ),
                )

        if quantity <= 0:
            return render(
                request,
                self.template_name,
                self.get_context(
                    order,
                    quantity=quantity_raw,
                    units_count=units_count_raw,
                    selected_palette_id=palette_id,
                    error="Ilość sztuk musi być większa od zera.",
                ),
            )

        if units_count <= 0:
            return render(
                request,
                self.template_name,
                self.get_context(
                    order,
                    quantity=quantity_raw,
                    units_count=units_count_raw,
                    selected_palette_id=palette_id,
                    error="Liczba jednostek musi być większa od zera.",
                ),
            )

        if units_count > 100:
            return render(
                request,
                self.template_name,
                self.get_context(
                    order,
                    quantity=quantity_raw,
                    units_count=units_count_raw,
                    selected_palette_id=palette_id,
                    error="Jednorazowo możesz dodać maksymalnie 100 jednostek.",
                ),
            )

        with transaction.atomic():
            for _ in range(units_count):
                ShipmentUnit.objects.create(
                    order=order,
                    quantity=quantity,
                    palette=palette,
                    created_by=request.user,
                )

        messages.success(
            request,
            (
                f"Dodano {units_count} "
                f"{'jednostkę' if units_count == 1 else 'jednostki/jednostek'} "
                f"po {quantity} szt."
            ),
        )

        return redirect(
            "warehouse:shipment-unit-create",
            order_id=order.id,
        )



from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import FileResponse
from django.urls import reverse_lazy
from django.views import View

from warehouse.models import ShipmentUnit
from warehouse.services.shipment_unit_pdf import ShipmentUnitPDF


class ShipmentUnitPrintView(
    LoginRequiredMixin,
    View,
):
    login_url = reverse_lazy("login")

    def get(
        self,
        request,
        shipment_unit_id,
    ):
        shipment_unit = get_object_or_404(
            ShipmentUnit.objects.select_related(
                "order",
                "order__provider",
                "order__customer",
                "order__product",
                "product",
                "palette",
                "created_by",
            ),
            id=shipment_unit_id,
        )

        pdf_buffer = ShipmentUnitPDF(
            request=request,
            shipment_unit=shipment_unit,
        ).build()

        filename = (
            f"paletowka-"
            f"{shipment_unit.id}.pdf"
        )

        response = FileResponse(
            pdf_buffer,
            content_type="application/pdf",
        )

        response["Content-Disposition"] = (
            f'inline; filename="{filename}"'
        )

        return response


class ShipmentUnitsPrintAllView(LoginRequiredMixin, View):
    login_url = reverse_lazy("login")
    template_name = "warehouse/shipment_units_print_all.html"

    def get(self, request, order_id):
        order = get_object_or_404(
            Order.objects.select_related("product"),
            id=order_id,
        )

        shipment_units = (
            ShipmentUnit.objects
            .filter(order=order)
            .select_related(
                "order",
                "product",
                "palette",
                "created_by",
            )
            .order_by("created", "id")
        )

        return render(request, self.template_name, {
            "order": order,
            "shipment_units": shipment_units,
        })


class ShipmentUnitUpdateView(
    LoginRequiredMixin,
    ShipmentUnitOwnerRequiredMixin,
    View,
):
    login_url = reverse_lazy("login")
    template_name = "warehouse/shipment_unit_update.html"

    def get_context(self, shipment_unit, **kwargs):
        context = {
            "shipment_unit": shipment_unit,
            "order": shipment_unit.order,
            "palettes": Palette.objects.all().order_by("name"),
        }

        context.update(kwargs)
        return context

    def get(self, request, shipment_unit_id):
        self.check_shipment_unit_permission()

        shipment_unit = self.get_shipment_unit()

        return render(
            request,
            self.template_name,
            self.get_context(shipment_unit),
        )

    def post(self, request, shipment_unit_id):
        self.check_shipment_unit_permission()

        shipment_unit = self.get_shipment_unit()

        quantity_raw = request.POST.get("quantity")
        palette_id = request.POST.get("palette")

        try:
            quantity = int(quantity_raw)
        except (TypeError, ValueError):
            quantity = 0

        if quantity <= 0:
            return render(
                request,
                self.template_name,
                self.get_context(
                    shipment_unit,
                    quantity=quantity_raw,
                    selected_palette_id=palette_id,
                    error="Ilość musi być większa od zera.",
                ),
            )

        palette = None

        if palette_id:
            palette = Palette.objects.filter(id=palette_id).first()

            if not palette:
                return render(
                    request,
                    self.template_name,
                    self.get_context(
                        shipment_unit,
                        quantity=quantity_raw,
                        selected_palette_id=palette_id,
                        error="Wybrana paleta nie istnieje.",
                    ),
                )

        # Nie zapisujemy historii, jeśli faktycznie nic się nie zmieniło
        quantity_changed = shipment_unit.quantity != quantity
        palette_changed = shipment_unit.palette_id != (
            palette.id if palette else None
        )

        if not quantity_changed and not palette_changed:
            messages.info(
                request,
                f"Nie wprowadzono zmian w jednostce #{shipment_unit.id}.",
            )

            return redirect(
                "warehouse:shipment-unit-create",
                order_id=shipment_unit.order_id,
            )

        with transaction.atomic():
            # Historia przechowuje stan przed zmianą
            create_shipment_unit_history(
                shipment_unit=shipment_unit,
                user=request.user,
                action=ShipmentUnitHistory.ACTION_UPDATE,
            )

            shipment_unit.quantity = quantity
            shipment_unit.palette = palette
            shipment_unit.save()

        messages.success(
            request,
            f"Jednostka #{shipment_unit.id} została zaktualizowana.",
        )

        return redirect(
            "warehouse:shipment-unit-create",
            order_id=shipment_unit.order_id,
        )


class ShipmentUnitDeleteView(
    LoginRequiredMixin,
    ShipmentUnitOwnerRequiredMixin,
    View,
):
    login_url = reverse_lazy("login")

    def post(self, request, shipment_unit_id):
        self.check_shipment_unit_permission()

        shipment_unit = self.get_shipment_unit()

        order_id = shipment_unit.order_id
        deleted_unit_id = shipment_unit.id

        with transaction.atomic():
            create_shipment_unit_history(
                shipment_unit=shipment_unit,
                user=request.user,
                action=ShipmentUnitHistory.ACTION_DELETE,
            )

            shipment_unit.delete()

        messages.success(
            request,
            f"Jednostka #{deleted_unit_id} została usunięta.",
        )

        return redirect(
            "warehouse:shipment-unit-create",
            order_id=order_id,
        )


from django.contrib.auth.mixins import LoginRequiredMixin
from django.core import signing
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.views import View

def get_active_shipment(user):
    shipment, _created = Shipment.objects.get_or_create(
        created_by=user,
        status=Shipment.STATUS_DRAFT
    )

    return shipment


from django.core import signing
from django.db import IntegrityError, transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin

from collections import defaultdict


def build_shipment_summary(items):
    """
    Grupowanie:
    klient -> produkt

    Dla każdego produktu:
    - suma sztuk,
    - liczba jednostek/palet,
    - liczba poszczególnych typów palet.
    """

    grouped = {}

    for item in items:
        shipment_unit = item.shipment_unit
        order = shipment_unit.order

        customer = order.customer
        product = shipment_unit.product or order.product
        palette = shipment_unit.palette

        customer_id = customer.id
        customer_name = str(customer)

        if product:
            product_id = product.id
            product_name = str(product)
        else:
            product_id = None
            product_name = "Brak produktu"

        palette_name = (
            str(palette)
            if palette
            else "Bez określonej palety"
        )

        if customer_id not in grouped:
            grouped[customer_id] = {
                "customer": customer,
                "customer_name": customer_name,
                "total_quantity": 0,
                "palettes_count": 0,
                "products": {},
            }

        customer_group = grouped[customer_id]

        product_key = product_id or f"none-{product_name}"

        if product_key not in customer_group["products"]:
            customer_group["products"][product_key] = {
                "product": product,
                "product_name": product_name,
                "total_quantity": 0,
                "palettes_count": 0,
                "palette_types": defaultdict(int),
            }

        product_group = customer_group["products"][product_key]

        quantity = int(shipment_unit.quantity or 0)

        product_group["total_quantity"] += quantity
        product_group["palettes_count"] += 1
        product_group["palette_types"][palette_name] += 1

        customer_group["total_quantity"] += quantity
        customer_group["palettes_count"] += 1

    result = []

    for customer_group in grouped.values():
        products = []

        for product_group in customer_group["products"].values():
            product_group["palette_types"] = [
                {
                    "name": palette_name,
                    "quantity": palette_quantity,
                }
                for palette_name, palette_quantity
                in sorted(product_group["palette_types"].items())
            ]

            products.append(product_group)

        products.sort(
            key=lambda row: row["product_name"].lower()
        )

        customer_group["products"] = products
        result.append(customer_group)

    result.sort(
        key=lambda row: row["customer_name"].lower()
    )

    return result


class ShipmentUnitLoadingScanView(LoginRequiredMixin, View):
    login_url = reverse_lazy("login")
    template_name = "warehouse/loading_scan.html"

    def get_shipment_unit(self, token):
        try:
            payload = signing.loads(
                token,
                salt="shipment-unit-loading",
            )
        except signing.BadSignature:
            raise Http404("Nieprawidłowy kod palety.")

        shipment_unit_id = payload.get("shipment_unit_id")

        if not shipment_unit_id:
            raise Http404(
                "Kod nie zawiera identyfikatora palety."
            )

        return get_object_or_404(
            ShipmentUnit.objects.select_related(
                "order",
                "order__customer",
                "order__provider",
                "order__product",
                "product",
                "palette",
                "created_by",
            ),
            id=shipment_unit_id,
        )

    def get_context(self, request, shipment_unit, token):
        visit_counter(request.user, "add_shipment_unit")
        active_shipment = get_active_shipment(request.user)

        shipment_items = (
            active_shipment.items
            .select_related(
                "shipment_unit",
                "shipment_unit__order",
                "shipment_unit__order__customer",
                "shipment_unit__order__product",
                "shipment_unit__product",
                "shipment_unit__palette",
                "scanned_by",
            )
            .order_by("-scanned_at", "-id")
        )

        existing_item = (
            ShipmentItem.objects
            .select_related("shipment")
            .filter(shipment_unit=shipment_unit)
            .first()
        )

        return {
            "shipment_unit": shipment_unit,
            "order": shipment_unit.order,
            "token": token,
            "active_shipment": active_shipment,
            "shipment_items": shipment_items,
            "existing_item": existing_item,
            "already_in_active_shipment": bool(
                existing_item
                and existing_item.shipment_id
                == active_shipment.id
            ),
            "used_in_other_shipment": bool(
                existing_item
                and existing_item.shipment_id
                != active_shipment.id
            ),
        }

    def get(self, request, token):
        shipment_unit = self.get_shipment_unit(token)

        return render(
            request,
            self.template_name,
            self.get_context(
                request,
                shipment_unit,
                token,
            ),
        )

    def post(self, request, token):
        shipment_unit = self.get_shipment_unit(token)

        try:
            with transaction.atomic():
                active_shipment = (
                    Shipment.objects
                    .select_for_update()
                    .get(
                        created_by=request.user,
                        status=Shipment.STATUS_DRAFT,
                    )
                )

                existing_item = (
                    ShipmentItem.objects
                    .select_for_update()
                    .filter(shipment_unit=shipment_unit)
                    .select_related("shipment")
                    .first()
                )

                if existing_item:
                    if (
                        existing_item.shipment_id
                        == active_shipment.id
                    ):
                        messages.info(
                            request,
                            (
                                f"Paleta #{shipment_unit.id} "
                                "jest już w tym załadunku."
                            ),
                        )
                    else:
                        messages.error(
                            request,
                            (
                                f"Paleta #{shipment_unit.id} "
                                "została już przypisana do "
                                f"wysyłki #{existing_item.shipment_id}."
                            ),
                        )

                    return redirect(
                        "warehouse:shipment-unit-loading-scan",
                        token=token,
                    )

                ShipmentItem.objects.create(
                    shipment=active_shipment,
                    shipment_unit=shipment_unit,
                    scanned_by=request.user,
                )

        except Shipment.DoesNotExist:
            active_shipment = get_active_shipment(
                request.user
            )

            try:
                ShipmentItem.objects.create(
                    shipment=active_shipment,
                    shipment_unit=shipment_unit,
                    scanned_by=request.user,
                )
            except IntegrityError:
                messages.error(
                    request,
                    "Ta paleta została już wykorzystana.",
                )

                return redirect(
                    "warehouse:shipment-unit-loading-scan",
                    token=token,
                )

        except IntegrityError:
            messages.error(
                request,
                "Ta paleta została już przypisana do wysyłki.",
            )

            return redirect(
                "warehouse:shipment-unit-loading-scan",
                token=token,
            )

        messages.success(
            request,
            (
                f"Dodano paletę #{shipment_unit.id} "
                "do aktywnego załadunku."
            ),
        )

        return redirect(
            "warehouse:shipment-unit-loading-scan",
            token=token,
        )


class ShipmentItemDeleteView(LoginRequiredMixin, View):
    login_url = reverse_lazy("login")

    def post(self, request, item_id):
        item = get_object_or_404(
            ShipmentItem.objects.select_related(
                "shipment",
                "shipment_unit",
            ),
            id=item_id,
            shipment__created_by=request.user,
            shipment__status=Shipment.STATUS_DRAFT,
        )

        shipment_id = item.shipment_id
        shipment_unit_id = item.shipment_unit_id

        item.delete()

        messages.success(
            request,
            (
                f"Usunięto paletę #{shipment_unit_id} "
                f"z załadunku #{shipment_id}."
            ),
        )

        return redirect(
            "warehouse:shipment-detail",
            shipment_id=shipment_id,
        )


class ActiveShipmentView(LoginRequiredMixin, View):
    login_url = reverse_lazy("login")
    template_name = "warehouse/shipment_detail.html"

    def get(self, request):
        shipment = get_active_shipment(request.user)

        items = list(
            shipment.items
            .select_related(
                "shipment_unit",
                "shipment_unit__order",
                "shipment_unit__order__customer",
                "shipment_unit__order__product",
                "shipment_unit__product",
                "shipment_unit__palette",
                "scanned_by",
            )
            .order_by("-scanned_at", "-id")
        )

        shipment_summary = build_shipment_summary(items)

        return render(
            request,
            self.template_name,
            {
                "shipment": shipment,
                "items": items,
                "shipment_summary": shipment_summary,
            },
        )


from django.utils import timezone


class ShipmentConfirmView(LoginRequiredMixin, View):
    login_url = reverse_lazy("login")

    def post(self, request, shipment_id):
        car_number = (
            request.POST.get("car_number") or ""
        ).strip()

        driver_name = (
            request.POST.get("driver_name") or ""
        ).strip()

        notes = (
            request.POST.get("notes") or ""
        ).strip()

        try:
            with transaction.atomic():
                shipment = get_object_or_404(
                    Shipment.objects.select_for_update(),
                    id=shipment_id,
                    created_by=request.user,
                    status=Shipment.STATUS_DRAFT,
                )

                if not shipment.items.exists():
                    messages.error(
                        request,
                        (
                            "Nie można potwierdzić pustego "
                            "załadunku."
                        ),
                    )

                    return redirect(
                        "warehouse:active-shipment"
                    )

                if not car_number:
                    messages.error(
                        request,
                        "Podaj numer rejestracyjny pojazdu.",
                    )

                    return redirect(
                        "warehouse:active-shipment"
                    )

                shipment.car_number = car_number
                shipment.driver_name = driver_name
                shipment.notes = notes
                shipment.status = Shipment.STATUS_CONFIRMED
                shipment.confirmed_by = request.user
                shipment.confirmed_at = timezone.now()

                shipment.save(
                    update_fields=[
                        "car_number",
                        "driver_name",
                        "notes",
                        "status",
                        "confirmed_by",
                        "confirmed_at",
                    ]
                )

        except Exception as e:
            messages.error(
                request,
                f"Nie udało się potwierdzić załadunku: {e}",
            )

            return redirect(
                "warehouse:active-shipment"
            )

        messages.success(
            request,
            f"Załadunek #{shipment.id} został potwierdzony.",
        )

        return redirect(
            "warehouse:shipment-detail",
            shipment_id=shipment.id,
        )

class ShipmentDetailView(LoginRequiredMixin, View):
    login_url = reverse_lazy("login")
    template_name = "warehouse/shipment_detail.html"

    def get(self, request, shipment_id):
        shipment = get_object_or_404(
            Shipment.objects.select_related(
                "created_by",
                "confirmed_by",
            ),
            id=shipment_id,
        )

        items = list(
            shipment.items
            .select_related(
                "shipment_unit",
                "shipment_unit__order",
                "shipment_unit__order__customer",
                "shipment_unit__order__product",
                "shipment_unit__product",
                "shipment_unit__palette",
                "scanned_by",
            )
            .order_by("-scanned_at", "-id")
        )

        shipment_summary = build_shipment_summary(items)

        return render(
            request,
            self.template_name,
            {
                "shipment": shipment,
                "items": items,
                "shipment_summary": shipment_summary,
            },
        )


from django.core.paginator import Paginator
from django.db.models import Count, Sum, Q
from django.db.models.functions import Coalesce


class ShipmentListView(LoginRequiredMixin, View):
    login_url = reverse_lazy("login")
    template_name = "warehouse/shipment_list.html"
    archive_page_size = 20

    def get(self, request):
        search = (request.GET.get("q") or "").strip()

        base_queryset = (
            Shipment.objects
            .select_related(
                "created_by",
                "confirmed_by",
            )
            .annotate(
                annotated_units_count=Count(
                    "items",
                    distinct=True,
                ),
                annotated_total_quantity=Coalesce(
                    Sum("items__shipment_unit__quantity"),
                    0,
                ),
            )
        )

        active_shipments = (
            base_queryset
            .filter(status=Shipment.STATUS_DRAFT)
            .order_by("-created_at", "-id")
        )

        archived_shipments = (
            base_queryset
            .exclude(status=Shipment.STATUS_DRAFT)
        )

        if search:
            archive_filters = (
                Q(car_number__icontains=search)
                | Q(driver_name__icontains=search)
                | Q(created_by__username__icontains=search)
                | Q(created_by__first_name__icontains=search)
                | Q(created_by__last_name__icontains=search)
                | Q(confirmed_by__username__icontains=search)
            )

            if search.isdigit():
                archive_filters |= Q(id=int(search))

            archived_shipments = archived_shipments.filter(
                archive_filters
            )

        archived_shipments = archived_shipments.order_by(
            "-confirmed_at",
            "-created_at",
            "-id",
        )

        paginator = Paginator(
            archived_shipments,
            self.archive_page_size,
        )

        archive_page = paginator.get_page(
            request.GET.get("page", 1)
        )

        own_active_shipment = (
            active_shipments
            .filter(created_by=request.user)
            .first()
        )

        return render(
            request,
            self.template_name,
            {
                "active_shipments": active_shipments,
                "archive_page": archive_page,
                "search": search,
                "own_active_shipment": own_active_shipment,
            },
        )
