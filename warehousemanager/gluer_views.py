from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin

from warehousemanager.forms import *


class NewGluerNumberAdd(PermissionRequiredMixin, View):
    permission_required = 'warehousemanager.add_gluernumber'

    def get(self, request):
        form = GluerNumberForm()
        context = {"form": form}
        return render(request, 'whm/gluer_number-add.html', context=context)

    def post(self, request):
        form = GluerNumberForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect('gluernumbers')
