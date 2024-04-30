from django.shortcuts import render, HttpResponse
from django.views import View

from orders.forms import *
from orders.models import *


'''class AddProduct(View):
    def get(self, request):
        form = ProductForm()
        return render(request, 'orders/product_new.html', locals())

    def post(self, request):
        form = ProductForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            type_ = data['type']
            description = data['description']
            dimensions = data['dimensions']
            cardboard = data['cardboard']

            Product.objects.create(type=type_, description=description, dimensions=dimensions, cardboard=cardboard)

            return HttpResponse('Product created!')'''


class OrdersView(View):
    def get(self, request):
        orders = OrderProduct.objects.filter(realized=False)
        orders = sorted(orders, key=lambda x: x.time_to_realize())
        return render(request, 'orders/orders-list.html', locals())


class CardboardOrders(View):
    def get(self, request):
        orders = CardboardOrder.objects.all()

        return render(request, "orders/cardboard-orders.html", locals())

