from django.shortcuts import render, HttpResponse
from django.views import View

from warehouse.gs_connection import *


class TestView(View):
    def get(self, request):
        return HttpResponse(f'{get_data(1105)}')
