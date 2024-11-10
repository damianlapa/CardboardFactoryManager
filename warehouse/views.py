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
                    customer = Buyer.objects.get(name=data[18])
                except Buyer.DoesNotExist:
                    customer = Buyer(name=data[18], shortcut=data[18][:5])
                    customer.save()

                try:
                    provider = Provider.objects.get(shortcut=data[0])
                except Provider.DoesNotExist:
                    provider = Provider(name=data[0], shortcut=data[0])
                    provider.save()

                try:
                    product = Product.objects.get(name=f'{data[23]} {data[18]}')
                except Product.DoesNotExist:
                    product = Product(name=f'{data[23]} {data[18]}')
                    product.save()
                try:
                    order = Order.objects.get(order_id=f'{data[1]}/{data[2]}')
                    result += f'{order} already exists<br>'
                except Order.DoesNotExist:
                    order = Order(
                        customer=customer,
                        provider=provider,
                        order_id=f'{data[1]}/{data[2]}',
                        customer_date=data[5] if data[5] else None,
                        order_date=data[6] if data[6] else None,
                        delivery_date=data[7] if data[7] else None,
                        production_date=None,
                        dimensions=f'{data[12]}x{data[13]}',
                        name=data[19],
                        weight=0,
                        order_quantity=data[14],
                        delivered_quantity=data[15] if data[15] else 0,
                        price=int(float(data[22].replace('\xa0', '').replace(',', '.'))) if data[22] else 0,
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

        # Podział tekstu na linie
        lines = all_text.splitlines()

        wz_number = ''
        registration_plate = ''
        orders = []

        for num in range(len(lines)):
            line = lines[num]
            if "Kopia WZ Nr." in line and not wz_number:
                wz_number = line.split('.:')[1].strip()
            if "Nr rej./Nazwisko" in line and not registration_plate:
                registration_plate = line.split('.:')[1].split('/')[0].strip()
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

        # print(wz_number)
        # print(registration_plate)
        for o in orders:
            result += f'{o}<br>'
        return HttpResponse(result)




