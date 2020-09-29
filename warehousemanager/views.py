from django.shortcuts import render
from django.http import HttpResponse
from django.views import View
import json

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
        item_sorts = ITEM_SORTS
        buyers = Buyer.objects.all()
        cardboard_types = CARDBOARD_TYPES
        return render(request, 'warehousemanager-new-order.html', locals())


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
        form = CardboardProviderForm()
        return render(request, 'new_provider.html', locals())

    def post(self, request):
        form = CardboardProviderForm(request.POST)
        if form.is_valid():
            new_provider = CardboardProvider(name=form.cleaned_data['name'])
            new_provider.save()
            return HttpResponse('ok')


