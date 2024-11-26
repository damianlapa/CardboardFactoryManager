# from django.shortcuts import render, HttpResponse, redirect
# from django.views import View
#
# from django.http import JsonResponse
# from django.shortcuts import get_object_or_404
# from django.contrib.auth.decorators import permission_required
# from django.utils.decorators import method_decorator
# from django.db.models.deletion import ProtectedError
#
# from warehouse.gs_connection import *
# from warehouse.models import *
# from warehousemanager.models import Buyer
#
# from production.models import ProductionOrder, ProductionUnit
#
# import pandas as pd
# import pdfplumber
#
# from django.views.generic import ListView
#
# from django.db import transaction
#
#
# def delete_delivery_ajax(request, delivery_id):
#     if request.method == "POST":
#         delivery = get_object_or_404(Delivery, id=delivery_id)
#
#         try:
#             # Obsługa relacji (z `related_name` lub bez)
#             with transaction.atomic():
#                 delivery.deliverypalette_set.all().delete()
#                 delivery.deliveryitem_set.all().delete()
#                 delivery.delete()
#         except ProtectedError:
#             return JsonResponse({"success": False,
#                                  "message": f"Delivery {delivery.number} can not be deleted. One or more delivery item is already added to stock."})
#
#         return JsonResponse({"success": True, "message": f"Delivery {delivery.number} deleted successfully."})
#     return JsonResponse({"success": False, "message": "Invalid request method."})
#
#
# class TestView(View):
#     def get(self, request):
#         data_all = get_all()
#         result = ''
#         row = request.GET.get('row')
#         division = request.GET.get('division')
#         if row:
#             row = int(row)
#         else:
#             row = 1105
#
#         if division:
#             start, end = division.split(',')
#             rows = [r for r in range(int(start), int(end) + 1)]
#         else:
#             rows = [row]
#
#         for row in rows:
#             try:
#                 data = data_all[row]
#
#                 try:
#                     customer = Buyer.objects.get(name=data[18].upper().strip())
#                 except Buyer.DoesNotExist:
#                     customer = Buyer(name=data[18].upper().strip(), shortcut=data[18].upper().strip()[:5])
#                     customer.save()
#
#                 try:
#                     provider = Provider.objects.get(shortcut=data[0].upper().strip())
#                 except Provider.DoesNotExist:
#                     provider = Provider(name=data[0], shortcut=data[0])
#                     provider.save()
#
#                 try:
#                     product = Product.objects.get(name=f'{data[18].upper().strip()} {data[23].upper().strip()}')
#                 except Product.DoesNotExist:
#                     product = Product(name=f'{data[18].upper().strip()} {data[23].upper().strip()}')
#                     product.save()
#                 try:
#                     order = Order.objects.get(order_id=f'{data[1].upper().strip()}/{data[2].upper().strip()}',
#                                               provider=Provider.objects.get(shortcut=data[0].upper().strip()))
#                     result += f'{order} already exists<br>'
#                 except Order.DoesNotExist:
#                     order = Order(
#                         customer=customer,
#                         provider=provider,
#                         order_id=f'{data[1].upper().strip()}/{data[2].upper().strip()}',
#                         customer_date=data[5].upper().strip() if data[5].upper().strip() else data[6].upper().strip(),
#                         order_date=data[6].upper().strip() if data[6].upper().strip() else None,
#                         order_year=data[5][:4] if data[5] else data[6][:4],
#                         delivery_date=data[7].upper().strip() if data[7].upper().strip() else None,
#                         production_date=None,
#                         dimensions=f'{data[12].upper().strip()}x{data[13].upper().strip()}',
#                         name=data[19].upper().strip(),
#                         weight=0,
#                         order_quantity=data[14].upper().strip(),
#                         delivered_quantity=data[15].upper().strip() if data[15].upper().strip() else 0,
#                         price=int(float(data[22].upper().strip().replace('\xa0', '').replace(',', '.'))) if data[
#                             22] else 0,
#                         product=product
#                     )
#                     order.save()
#                     result += f'{order} saved<br>'
#
#             except Exception as e:
#                 result += f'{e}<br>'
#         return HttpResponse(result)
#
#
# class LoadExcelView(View):
#     def get(self, request):
#         return render(request, "warehouse/load_excel.html")
#
#     def post(self, request):
#         result = ''
#         # Odczytaj plik Excel bezpośrednio z pamięci
#         excel_file = request.FILES["excel_file"]
#
#         # Wczytaj dane z Excela bez zapisywania pliku
#         df = pd.read_excel(excel_file, engine="openpyxl")
#
#         # Przechodzenie przez wiersze i zapisywanie w bazie
#         for _, row in df.iterrows():
#             result += f'{row["DATA DOSTAWY"]} {row["NR WZ."]}<br>'
#
#         return HttpResponse(result)
#         # if request.method == "POST" and request.FILES["excel_file"]:
#
#
# class LoadWZ(View):
#     def get(self, request):
#         return render(request, "warehouse/load_wz.html")
#
#     def post(self, request):
#         if "wz_file" not in request.FILES:
#             return render(request, "warehouse/load_wz_result.html", {
#                 "errors": ["No file was uploaded. Please select a file and try again."]
#             })
#         result = []
#         pdf_file = request.FILES["wz_file"]
#         errors = []
#
#         with pdfplumber.open(pdf_file) as pdf:
#             all_text = ""
#             for page in pdf.pages:
#                 all_text += page.extract_text() + "\n"
#
#         lines = all_text.splitlines()
#
#         provider = ''
#         wz_number = ''
#         car_number = ''
#         date = ''
#         phone = ''
#         palettes = ''
#         orders = []
#         p_quantity = ''
#         order_num = 1
#         number = ''
#
#         cardboard = ''
#         dimensions = ''
#         quantity = ''
#         order_numbers = []
#
#         if 'tfp' in all_text or 'TFP' in all_text:
#
#             for num in range(len(lines)):
#                 line = lines[num]
#                 if 'TFP Sp. z o.o.' in line:
#                     provider = "TFP"
#                 if "Data..." in line:
#                     date = line.split('.:')[1].strip()
#                 if "( " in line and " )" in line:
#                     phone = line.replace("( ", "").replace(" )", "").strip()
#                 if "Kopia WZ Nr." in line and not wz_number:
#                     wz_number = line.split('.:')[1].strip()
#                 if "Nr rej./Nazwisko" in line and not car_number:
#                     car_number = line.split('.:')[1].split('/')[0].strip()
#                 if "Rodzaj palety Typ platności Ilość pobrana" in line:
#                     p_line = lines[num + 1]
#                     p_line = p_line.split(' ')
#                     palettes = f'{p_line[0]};{p_line[1]};{p_line[3].split(",")[0]}'
#                 if "Nr zam. klienta:" in line:
#                     number = line.split("Nr zam. klienta:")[1].split(" ")[0].strip()
#                     orders.append([number, cardboard, dimensions, quantity])
#                 if len(line.split(' ')) == 5 or len(line.split(' ')) == 6:
#                     line = line.split(' ')
#                     if line[0][0].isdigit() and line[1][-1] == '\xad' and 'x' in line[2]:
#                         cardboard = line[1][:-1]
#                         dimensions = line[2]
#                         quantity = line[3].split(',')[0] if len(line) == 5 else f'{line[3]}{line[4]}'.split(',')[0]
#
#                 if "Ilość na palecie: " in line:
#                     if order_num == len(orders):
#                         p_quantity += f'{line.split("palecie:")[1].split(",")[0].strip().replace(" ", "")};'
#                     else:
#                         orders[-2].append(p_quantity)
#                         order_num += 1
#                         p_quantity = f'{line.split("palecie:")[1].split(",")[0].strip().replace(" ", "")};'
#
#             orders[-1].append(p_quantity)
#
#             date = date.replace('­', '.').split('.')
#             if int(date[0]) > 31:
#                 date = (date[2], date[1], date[0])
#
#         else:
#             for num in range(len(lines)):
#                 line = lines[num]
#                 if 'JASSBOARD SP. Z O.O.' in line:
#                     provider = "JASS"
#                 if "Data wystawienia: " in line:
#                     date = line.split('wystawienia: ')[1].strip().replace('-', '.').split('.')
#                     date = date[2], date[1], date[0]
#                 if "Nr rejestracyjny: " in line:
#                     phone, car_number = line.split("Nr rejestracyjny: ")[1].split(' ')
#                 if "Numer WZ" in line and not wz_number:
#                     wz_number = lines[num + 1].strip()
#                 if "PALETA" in line:
#                     p_line = line.split(' ')
#                     palette = p_line[0].split('_')
#                     palette_type = 'Paleta'
#                     if palette[1] == 'EURO':
#                         palette_type = 'EPAL'
#                     palette_dimensions = palette[2].lower().split('x')
#                     palette_dimensions = f'{palette_dimensions[1]}x{palette_dimensions[0]}'
#                     palettes = f'{palette_type};{palette_dimensions};{p_line[1]}'
#                 if "nr zam.:" in line.lower():
#                     number = line.lower().split("nr zam.:")[1].replace('jass', '').strip()
#                     if number not in order_numbers:
#                         order_numbers.append(number)
#                 if "ark" in line and 'm2' in line and not "RAZEM" in line and not 'Ilość wysłana' in line:
#                     cardboard_line = line.split(' ')
#                     cardboard = cardboard_line[1][:-9] if cardboard_line[1][2].isdigit() else cardboard_line[1][:-8]
#                     dimensions = cardboard_line[1][-9:] if cardboard_line[1][2].isdigit() else cardboard_line[1][-8:]
#                     p_quantity += f'{cardboard_line[3]};'
#                 if cardboard in line and "RAZEM" in line:
#                     quantity_line = line.split(" ")
#                     quantity = quantity_line[3].replace(',', '')
#                     if len(dimensions) == 9:
#                         dimensions_data = dimensions.split('*')
#                     else:
#                         dimensions_data = dimensions[:-4], dimensions[4:]
#                     dimensions = f'{str(int(dimensions_data[1]))}x{str(int(dimensions_data[0]))}'
#                     orders.append([number, cardboard, dimensions, quantity, p_quantity])
#                     p_quantity = ''
#
#         try:
#             palette = Palette.objects.get(name=f'{palettes.split(";")[0]} {palettes.split(";")[1]}')
#         except Palette.DoesNotExist:
#             palette = Palette.objects.create(name=f'{palettes.split(";")[0]} {palettes.split(";")[1]}')
#             palette.save()
#
#         try:
#             delivery, created = Delivery.objects.get_or_create(
#                 number=wz_number,
#                 defaults={
#                     'provider': Provider.objects.get(shortcut=provider),
#                     'date': datetime.date(int(date[2]), int(date[1]), int(date[0])),
#                     'car_number': car_number,
#                     'telephone': phone.replace(' ', ''),
#                 }
#             )
#             if not created:
#                 errors.append(f'Delivery with number {wz_number} already exists.<br>')
#                 return render(request, "warehouse/load_wz_result.html", {
#                     "errors": errors
#                 })
#
#             delivery_palette = DeliveryPalette.objects.create(
#                 delivery=delivery,
#                 palette=palette,
#                 quantity=int(palettes.split(';')[2])
#             )
#             delivery_palette.save()
#
#         except Provider.DoesNotExist:
#             errors.append(f'Provider {provider} does not exist.')
#         except Exception as e:
#             errors.append(f'Error creating delivery: {str(e)}')
#
#         for order in orders:
#             try:
#                 p_quantity_counted = 0
#                 for p in order[4].split(';'):
#                     if p:
#                         p_quantity_counted += int(p)
#                 if p_quantity_counted != int(order[3]):
#                     order[3] = p_quantity_counted
#                     result.append(f'Order {order[0]}: Quantity corrected to {p_quantity_counted}')
#             except Exception as e:
#                 errors.append(f'Error with order {order[0]}: {str(e)}')
#             try:
#                 delivery_item = DeliveryItem.objects.create(
#                     delivery=delivery,
#                     order=Order.objects.get(provider=delivery.provider, order_id=order[0]),
#                     quantity=order[3],
#                     palettes_quantity=order[4]
#                 )
#                 delivery_item.save()
#                 result.append(f'Order {order[0]} successfully linked to delivery.')
#             except Order.DoesNotExist:
#                 errors.append(f'Order {order[0]} does not exist for provider {delivery.provider}.')
#             except Exception as e:
#                 errors.append(f'Error with delivery item for order {order[0]}: {str(e)}')
#
#         return render(request, "warehouse/load_wz_result.html", {"results": result, "errors": errors})
#
#
# class OrderListView(View):
#     def get(self, request):
#         orders = Order.objects.all()
#         # paginate_by = 10  # optional: pagination to limit orders per page
#         return render(request, 'warehouse/order_list.html', locals())
#
#
# class OrderDetailView(View):
#     def get(self, request, order_id):
#         order = Order.objects.get(id=order_id)
#         items = DeliveryItem.objects.filter(order=order)
#         stock_supplies = StockSupply.objects.filter(delivery_item__in=items)
#         stock_materials = []
#         for stock_supply in stock_supplies:
#             try:
#                 stock = Stock.objects.get(name=stock_supply.name)
#                 stock_materials.append(stock)
#
#             except Exception as e:
#                 pass
#         print(stock_supplies, stock_materials)
#         stocks = StockSupply.objects.all()
#
#         try:
#             production_order = ProductionOrder.objects.get(id_number=f'{order.provider} {order.order_id}')
#             production_units = ProductionUnit.objects.filter(production_order=production_order).order_by('sequence')
#         except ProductionOrder.DoesNotExist:
#             production_units = []
#         return render(request, 'warehouse/order_details.html', locals())
#
#
# class DeliveriesView(View):
#     def get(self, request):
#         deliveries = Delivery.objects.all().prefetch_related('deliverypalette_set__palette')
#         return render(request, 'warehouse/delivery_list.html', locals())
#
#
# class DeliveryDetailView(View):
#     def get(self, request, delivery_id):
#         delivery = Delivery.objects.get(id=delivery_id)
#         items = DeliveryItem.objects.filter(delivery=delivery)
#         return render(request, 'warehouse/delivery_details.html', locals())
#
#
# class AddDeliveryToWarehouse(View):
#     def post(self, request, delivery_id):
#         delivery = Delivery.objects.get(id=delivery_id)
#         items = DeliveryItem.objects.filter(delivery=delivery)
#         delivery.add_to_warehouse()
#
#         return redirect("delivery-detail-view", delivery_id=delivery_id)
#
#
# class WarehouseView(View):
#     def get(self, request, warehouse_id):
#         warehouse = Warehouse.objects.get(id=warehouse_id)
#         stocks = WarehouseStock.objects.filter(warehouse=warehouse)
#         print(stocks)
#         return render(request, 'warehouse/warehouse_details.html', locals())
#
#
# class WarehouseListView(View):
#     def get(self, request):
#         warehouses = Warehouse.objects.all()
#         return render(request, 'warehouse/warehouse_list.html', locals())
