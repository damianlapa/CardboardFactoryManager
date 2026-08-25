from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views import View

from paker.services.dashboard import (
    get_dashboard_context,
)


class DashboardView(
    LoginRequiredMixin,
    View,
):
    login_url = reverse_lazy("login")
    template_name = "dashboard/index.html"

    def get(self, request):
        context = get_dashboard_context(
            user=request.user,
        )

        return render(
            request,
            self.template_name,
            context,
        )