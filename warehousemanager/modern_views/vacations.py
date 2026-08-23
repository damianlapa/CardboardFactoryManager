from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import render
from django.views import View

from warehousemanager.services.vacations import (
    get_available_vacation_years,
    get_vacation_balances,
    get_vacation_details,
    resolve_vacation_year,
)


class ModernVacationListView(
    PermissionRequiredMixin,
    View,
):
    permission_required = "warehousemanager.view_absence"
    template_name = "modern/vacations/list.html"

    def get(self, request):
        year = resolve_vacation_year(
            request.GET.get("year")
        )

        context = {
            "title": "Urlopy",
            "year": year,
            "previous_year": year - 1,
            "years": get_available_vacation_years(),
            "vacation_balances": get_vacation_balances(
                user=request.user,
                year=year,
            ),
        }

        return render(
            request,
            self.template_name,
            context,
        )


class ModernVacationDetailView(
    PermissionRequiredMixin,
    View,
):
    permission_required = "warehousemanager.view_absence"
    template_name = "modern/vacations/detail.html"

    def get(self, request, person_id):
        year = resolve_vacation_year(
            request.GET.get("year")
        )

        context = get_vacation_details(
            user=request.user,
            person_id=person_id,
            year=year,
        )

        context["title"] = "Szczegóły urlopu"
        context["years"] = get_available_vacation_years()

        return render(
            request,
            self.template_name,
            context,
        )