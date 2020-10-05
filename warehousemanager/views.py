from django.shortcuts import render, redirect
from django.urls import reverse
from django.http import HttpResponse
from django.views import View
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
        return render(request, 'warehousemanager-all-orders-details.html', locals())


class NewOrder(View):
    def get(self, request):
        providers = CardboardProvider.objects.all()
        form = NewOrderForm()
        return render(request, 'warehousemanager-new-order.html', locals())

    def post(self, request):
        order_id = Order.objects.all().order_by('id').reverse()[0].id
        for order in Order.objects.all().reverse():
            print(order.id)
        return redirect('/add-items/{}'.format(order_id))


class NewOrderAdd(View):
    def get(self, request):
        provider_num = request.GET.get('provider_num')
        provider = CardboardProvider.objects.get(id=int(provider_num))
        all_orders = Order.objects.all().filter(provider=provider).order_by('order_provider_number')
        print(all_orders.reverse()[0])
        num = all_orders.reverse()[0].order_provider_number + 1
        new_order = Order.objects.create(provider=provider, order_provider_number=num, date_of_order=datetime.datetime.now())
        new_order.save()

        return HttpResponse('')


class NewItemAdd(View):
    def get(self, request, order_id):
        form = NewOrderForm()
        order = Order.objects.get(id=order_id)
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
        all_orders = Order.objects.all().filter(provider=provider)
        num = all_orders.count() + 1

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


