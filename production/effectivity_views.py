from django.shortcuts import render, HttpResponse, redirect
from django.views import View

from production.models import WorkStation


class OEEView(View):
    def get(self, request, year, month):
        workstations = WorkStation.objects.all()
        result = ''
        for w in workstations:
            result += f'{w.name:40} - {w.oee_factor(year, month)}</br>'
        return HttpResponse(result)