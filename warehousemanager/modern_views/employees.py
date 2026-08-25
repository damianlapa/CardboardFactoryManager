from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views import View

from paker.access.employees import (
    can_view_employee_list,
)
from warehousemanager.services.employees import (
    get_employee_details,
    get_employee_list,
)


class ModernEmployeeListView(
    LoginRequiredMixin,
    View,
):
    login_url = reverse_lazy("login")
    template_name = "employees/list.html"

    def get(self, request):
        if not can_view_employee_list(
            request.user
        ):
            raise PermissionDenied

        include_inactive = (
            request.GET.get("all") == "1"
        )

        context = {
            "employees": get_employee_list(
                include_inactive=include_inactive,
            ),
            "include_inactive":
                include_inactive,
        }

        return render(
            request,
            self.template_name,
            context,
        )


class ModernEmployeeDetailView(
    LoginRequiredMixin,
    View,
):
    login_url = reverse_lazy("login")
    template_name = "employees/detail.html"

    def get(self, request, person_id):
        context = get_employee_details(
            user=request.user,
            employee_id=person_id,
        )

        return render(
            request,
            self.template_name,
            context,
        )