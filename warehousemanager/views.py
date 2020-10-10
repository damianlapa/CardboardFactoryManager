from django.shortcuts import render, redirect
from django.urls import reverse
from django.http import HttpResponse
from django.views import View
from django.contrib import messages
import json
import datetime

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


class AllOrdersDetails(View):
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
        order_id = Order.objects.all().order_by('id').reverse()[0].id
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
        new_order = Order.objects.create(provider=provider, order_provider_number=num, date_of_order=datetime.datetime.now())
        new_order.save()

        return HttpResponse('')


class NewItemAdd(View):
    def get(self, request, order_id):
        form = NewOrderForm()
        order = Order.objects.get(id=order_id)
        items = OrderItem.objects.all().filter(order=order)
        last_items = OrderItem.objects.all().reverse()[:5]

        if order.is_completed:
            return HttpResponse('Zamówienie zostało już skompletowane')

        return render(request, 'add-item.html', locals())

    def post(self, request, order_id):
        form = NewOrderForm(request.POST)
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
        num = all_orders[0].order_provider_number + 1

        z = json.dumps(num)

        return HttpResponse(z)


class ProviderForm(View):
    def get(self, request):
        form = NewOrderForm()
        return render(request, 'new_provider.html', locals())

    def post(self, request):
        form = CardboardProviderForm(request.POST)
        if form.is_valid():
            return HttpResponse('ok')


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

        data = {
            'height': item.format_height,
            'width': item.format_width
        }

        return HttpResponse(json.dumps(data))
