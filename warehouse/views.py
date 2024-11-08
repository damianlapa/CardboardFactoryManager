from django.shortcuts import render, HttpResponse
from django.views import View

from warehouse.gs_connection import *
from warehouse.models import *
from warehousemanager.models import Buyer


class TestView(View):
    def get(self, request):
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
                data = get_data(row)

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
                        customer_date=data[5],
                        order_date=data[6],
                        delivery_date=data[7],
                        production_date=None,
                        dimensions=f'{data[12]}x{data[13]}',
                        name=data[19],
                        weight=0,
                        order_quantity=data[14],
                        delivered_quantity=data[15],
                        price=data[22],
                        product=product
                    )
                    order.save()
                    result += f'{order} saved<br>'

            except Exception as e:
                result += f'{e}<br>'
        return HttpResponse(result)


