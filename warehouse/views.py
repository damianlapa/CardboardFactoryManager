from django.shortcuts import render, HttpResponse
from django.views import View

from warehouse.gs_connection import *
from warehouse.models import *
from warehousemanager.models import Buyer

import pandas as pd
import pdfplumber


class TestView(View):
    def get(self, request):
        data_all = get_all()
        result = ''
        row = request.GET.get('row')
        division = request.GET.get('division')
        if row:
            row = int(row)
        else:
            row = 1105

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
                    product = Product.objects.get(name=f'{data[23].upper().strip()} {data[18].upper().strip()}')
                except Product.DoesNotExist:
                    product = Product(name=f'{data[23].upper().strip()} {data[18].upper().strip()}')
                    product.save()
                try:
                    order = Order.objects.get(order_id=f'{data[1].upper().strip()}/{data[2].upper().strip()}')
                    result += f'{order} already exists<br>'
                except Order.DoesNotExist:
                    order = Order(
                        customer=customer,
                        provider=provider,
                        order_id=f'{data[1].upper().strip()}/{data[2].upper().strip()}',
                        customer_date=data[5].upper().strip() if data[5].upper().strip() else data[6].upper().strip(),
                        order_date=data[6].upper().strip() if data[6].upper().strip() else None,
                        delivery_date=data[7].upper().strip() if data[7].upper().strip() else None,
                        production_date=None,
                        dimensions=f'{data[12].upper().strip()}x{data[13].upper().strip()}',
                        name=data[19].upper().strip(),
                        weight=0,
                        order_quantity=data[14].upper().strip(),
                        delivered_quantity=data[15].upper().strip() if data[15].upper().strip() else 0,
                        price=int(float(data[22].upper().strip().replace('\xa0', '').replace(',', '.'))) if data[22] else 0,
                        product=product
                    )
                    order.save()
                    result += f'{order} saved<br>'

            except Exception as e:
                result += f'{e}<br>'
        return HttpResponse(result)


class LoadExcelView(View):
    def get(self, request):
        return render(request, "warehouse/load_excel.html")
    def post(self, request):
        result = ''
        # Odczytaj plik Excel bezpośrednio z pamięci
        excel_file = request.FILES["excel_file"]

        # Wczytaj dane z Excela bez zapisywania pliku
        df = pd.read_excel(excel_file, engine="openpyxl")

        # Przechodzenie przez wiersze i zapisywanie w bazie
        for _, row in df.iterrows():
            result += f'{row["DATA DOSTAWY"]} {row["NR WZ."]}<br>'

        return HttpResponse(result)
        # if request.method == "POST" and request.FILES["excel_file"]:


class LoadWZ(View):
    def get(self, request):
        return render(request, "warehouse/load_wz.html")

    def post(self, request):
        result = ''
        pdf_file = request.FILES["wz_file"]

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
            if "Rodzaj palety Typ platności Ilość pobrana" in line:
                p_line = lines[num + 1]
                p_line = p_line.split(' ')
                palettes = f'{p_line[0]};{p_line[1]};{p_line[3].split(",")[0]}'
            if "Nr zam. klienta:" in line:
                number = line.split("Nr zam. klienta:")[1].split(" ")[0].strip()
                line_data = lines[num - 4].split(' ')
                cardboard = line_data[1].split('-')[0].strip().replace('\xad', '')
                dimensions = line_data[2]
                quantity = (line_data[3] + line_data[4]).split(',')[0]
                if cardboard == 'netto':
                    line_data = lines[num - 31].split(' ')
                    cardboard = line_data[1].split('-')[0].strip().replace('\xad', '')
                    dimensions = line_data[2]
                    quantity = (line_data[3] + line_data[4]).split(',')[0]
                orders.append([number, cardboard, dimensions, quantity])
            if "Ilość na palecie: " in line:
                print(order_num, len(orders) + 1)
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

        delivery = Delivery.objects.create(
            provider=Provider.objects.get(shortcut=provider),
            date=datetime.date(int(date[2]), int(date[1]), int(date[0])),
            car_number=car_number,
            telephone=phone.replace(' ', ''),
        )
        delivery.save()

        for order in orders:
            result += f'{order}<br>'
            try:
                delivery_item = DeliveryItem.objects.create(
                    delivery=delivery,
                    order=Order.objects.get(provider=delivery.provider, order_id=order[0]),
                    quantity=order[3],
                    palettes_quantity=order[4]
                )
                delivery_item.save()
            except Exception as e:
                result += f'{e}<br>'

        return HttpResponse(result)




