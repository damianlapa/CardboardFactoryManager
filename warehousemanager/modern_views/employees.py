from django.contrib.auth.mixins import (
    LoginRequiredMixin,
)
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views import View

from warehousemanager.services.employees import (
    get_employee_list,
)


class ModernEmployeeListView(
    LoginRequiredMixin,
    View,
):
    login_url = reverse_lazy("login")

    template_name = (
        "modern/employees/list.html"
    )

    def get(self, request):
        include_inactive = (
            request.GET.get("all") == "1"
        )

        context = {
            "include_inactive":
                include_inactive,

            "employees": get_employee_list(
                include_inactive=
                    include_inactive,
            ),
        }

        return render(
            request,
            self.template_name,
            context,
        )