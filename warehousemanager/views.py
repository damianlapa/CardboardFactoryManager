from django.shortcuts import render, redirect
from django.urls import reverse
from django.http import HttpResponse
from django.views import View
from django.contrib import messages
from django.http import FileResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import authenticate, login, logout
import io
import os
import shutil
from django.conf import settings
import docx
import json
import datetime

import subprocess
# import models from warehousemanager app
from warehousemanager.models import *
from warehousemanager.forms import *


def index(request):
    return HttpResponse('first view')


# view displays all orders
class Orders(View):

    def get(self, request):
        orders_all = Order.objects.all()
        return render(request, 'warehousemanager-orders.html', locals())


class OrdersDetails(View):

    def get(self, request, order_id):
        order = Order.objects.get(id=order_id)
        ordered_items = order.orderitem_set.all()
        return render(request, 'warehousemanager-order-details.html', locals())


class AllOrdersDetails(LoginRequiredMixin, View):
    login_url = '/'

    def get(self, request):
        orders = Order.objects.all()
        providers = CardboardProvider.objects.all()
        return render(request, 'warehousemanager-all-orders-details.html', locals())


class NewOrder(View):
    def get(self, request):
        providers = CardboardProvider.objects.all()
        form = NewOrderForm()

        # deleting orders without items
        orders = Order.objects.all()
        for order in orders:
            if not OrderItem.objects.all().filter(order=order):
                order.delete()

        not_completed_orders = Order.objects.all()

        for n_c_order in not_completed_orders:
            if not n_c_order.is_completed:
                messages.info(request, 'Masz niezakończone zamówienia')

        return render(request, 'warehousemanager-new-order.html', locals())

    def post(self, request):
        form = NewOrderForm(request.POST)
        if form.is_valid():
            provider = form.cleaned_data['provider']
            order_provider_number = form.cleaned_data['order_provider_number']
            date_of_order = form.cleaned_data['date_of_order']

            provider_object = CardboardProvider.objects.get(name=provider)

            new_order = Order.objects.create(provider=provider_object, order_provider_number=int(order_provider_number),
                                             date_of_order=datetime.datetime.now())

            new_order.save()

            orders = Order.objects.all()
            if orders:
                order_id = orders.order_by('id').reverse()[0].id
            else:
                order_id = 1
            return redirect('/add-items/{}'.format(order_id))


class DeleteOrder(View):
    def get(self, request):
        order_id = request.GET.get('order_id')
        Order.objects.get(id=order_id).delete()

        return redirect('/orders')


class NewOrderAdd(View):
    def get(self, request):
        provider_num = request.GET.get('provider_num')
        provider = CardboardProvider.objects.get(id=int(provider_num))
        all_orders = Order.objects.all().filter(provider=provider).order_by('order_provider_number')
        num = all_orders.reverse()[0].order_provider_number + 1
        new_order = Order.objects.create(provider=provider, order_provider_number=num,
                                         date_of_order=datetime.datetime.now())
        new_order.save()

        return HttpResponse('')


class NewItemAdd(View):
    def get(self, request, order_id):
        form = NewOrderItemForm()
        order = Order.objects.get(id=order_id)
        items = OrderItem.objects.all().filter(order=order)
        last_items = OrderItem.objects.all().reverse()[:5]
        all_items = OrderItem.objects.all()

        if order.is_completed:
            return HttpResponse('Zamówienie zostało już skompletowane')

        return render(request, 'add-item.html', locals())

    def post(self, request, order_id):
        form = NewOrderItemForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('/add-items/{}'.format(order_id))
        else:
            return HttpResponse(form.errors)


class NextOrderNumber(View):
    def get(self, request):
        provider_num = request.GET.get('provider_num')
        provider = CardboardProvider.objects.get(id=int(provider_num))
        all_orders = Order.objects.all().filter(provider=provider).order_by('order_provider_number').reverse()
        if all_orders:
            num = all_orders[0].order_provider_number + 1
        else:
            num = 1

        z = json.dumps(num)

        return HttpResponse(z)


class ProviderForm(View):
    def get(self, request):
        form = CardboardProviderForm()
        return render(request, 'new_provider.html', locals())

    def post(self, request):
        form = CardboardProviderForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            CardboardProvider.objects.create(name=name)

            return redirect('manage')


class NextItemNumber(View):
    def get(self, request):
        order_num = request.GET.get('order_num')
        order = Order.objects.get(id=int(order_num))
        all_items = OrderItem.objects.all().filter(order=order)

        num = len(all_items)

        return HttpResponse(json.dumps(num + 1))


class CompleteOrder(View):
    def get(self, request):
        order_id = int(request.GET.get('order_id'))
        order = Order.objects.get(id=order_id)
        order.is_completed = True
        order.save()

        return redirect('all-orders-details')


class GetItemDetails(View):
    def get(self, request):
        item_id = int(request.GET.get('item_id'))
        item = OrderItem.objects.get(id=item_id)

        if item.buyer.all():
            buyer = item.buyer.all()[0].name
        else:
            buyer = ''

        data = {
            'height': item.format_height,
            'width': item.format_width,
            'dimension_one': item.dimension_one,
            'dimension_two': item.dimension_two,
            'dimension_three': item.dimension_three,
            'sort': item.sort,
            'buyer': buyer,
            'weight': item.cardboard_weight,
            'cardboard_type': item.cardboard_type,
            'scores': item.scores
        }

        return HttpResponse(json.dumps(data))


class PrintTest(View):
    def get(self, request):
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer)
        p.drawString(100, 100, 'Hello World.')
        p.showPage()
        p.save()
        lpr = subprocess.Popen("/usr/bin/lpr", stdin=subprocess.PIPE)
        lpr.stdin.write(b'ok')
        buffer.seek(0)

        return FileResponse(buffer, as_attachment=True, filename='hello.pdf')


class OpenFile(View):
    def get(self, request, order_item_id):
        order_item = OrderItem.objects.get(id=order_item_id)

        os.chdir('/home/damian/PycharmProjects/PakerProject/media/paker')

        src = 'zp.docx'
        dst = 'zp{}'.format(order_item.id)

        os.rename(src, 'oko.docx')

        '''document = docx.Document('zp{}'.format(order_item.id))
        print(len(document.sections))

        text = ''

        for p in document.paragraphs:
            if p.text == 'TERMIN REALIZACJI':
                p.text = 'nowy termin'
            text += ' $'
            text += '<br />'
            text += p.text

        text += '<br />'
        text += 'Tabele <br />'

        for t in document.tables:
            text2 = ''
            for i, row in enumerate(t.rows):
                for c in row.cells:
                    if c.text == 'TYP MASZYNY':
                        if order_item.sort in ('201', '202', '203'):
                            c.text = 'f. ' + order_item.sort

                    text2 += c.text

            text += text2

        document.save('zp.docx')'''

        return HttpResponse('')


class NewAllOrders(View):
    def get(self, request):
        orders = Order.objects.all()
        providers = CardboardProvider.objects.all()
        quantities = OrderItemQuantity.objects.all()
        return render(request, 'new-all-orders.html', locals())


class StartPage(View):
    def get(self, request):
        user = request.user
        return render(request, 'start-page.html', locals())

    def post(self, request):
        name = request.POST.get('login')
        password = request.POST.get('password')

        user = authenticate(username=name, password=password)

        if user is not None:
            login(request, user)

        return redirect('start-page')


class LogoutView(View):
    def get(self, request):
        logout(request)

        return redirect('start-page')


class ManageView(LoginRequiredMixin, View):
    login_url = '/'

    def get(self, request):
        return render(request, 'warehousemanager-manage.html', locals())


# wszyscy dostawcy
class AllProvidersView(LoginRequiredMixin, View):
    login_url = '/'

    def get(self, request):
        providers = CardboardProvider.objects.all()
        return render(request, 'warehousemanager-all-providers.html', locals())
