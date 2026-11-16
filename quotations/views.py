from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views import View

from .services.dashboard import get_dashboard_context


class QuotationDashboardView(LoginRequiredMixin, View):
    login_url = "login"
    template_name = "quotations/dashboard.html"

    def get(self, request):
        return render(request, self.template_name, get_dashboard_context(request.GET))
