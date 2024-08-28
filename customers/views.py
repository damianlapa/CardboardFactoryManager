from django.shortcuts import render
from django.views import View

from .models import *
from .utils import *


class LoadOrders(View):
    def get(self, request):
        data = get_data(2024)

        return render(request, 'customers/all-orders.html', locals())
