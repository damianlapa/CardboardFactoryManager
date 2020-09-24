from django.shortcuts import render
from django.http import HttpResponse
from django.views import View

# import models from warehousemanager app
from warehousemanager.models import *


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

