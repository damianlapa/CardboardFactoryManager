from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.dateparse import parse_date
from django.views import View

from paker.access.employees import (
    can_view_employee_list,
)
from warehousemanager.models import Person, Contract
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
                user=request.user
            ),
            "include_inactive": include_inactive,
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
        from warehousemanager.models import OCCUPANCY_TYPE

        context = get_employee_details(
            user=request.user,
            employee_id=person_id
        )

        context['occupancy'] = OCCUPANCY_TYPE

        return render(
            request,
            self.template_name,
            context,
        )


class ModernEmployeeContractCreateView(
    LoginRequiredMixin,
    View,
):
    login_url = reverse_lazy("login")

    def post(self, request, person_id):
        employee = get_object_or_404(
            Person,
            pk=person_id,
        )

        # Korzystamy z tej samej kontroli dostępu,
        # którą już zwraca employee details.
        context = get_employee_details(
            user=request.user,
            employee_id=person_id,
        )

        access = context.get("access")

        if not access or not access.get("can_edit", False):
            raise PermissionDenied

        contract_type = request.POST.get(
            "type",
            "",
        ).strip()

        position = request.POST.get(
            "position",
            "",
        ).strip()

        date_start_raw = request.POST.get(
            "date_start",
            "",
        ).strip()

        date_end_raw = request.POST.get(
            "date_end",
            "",
        ).strip()

        salary_raw = request.POST.get(
            "salary",
            "",
        ).strip().replace(",", ".")

        extra_info = request.POST.get(
            "extra_info",
            "",
        ).strip()

        first = (
            request.POST.get("first") == "on"
        )

        # ========================================================
        # VALIDATION
        # ========================================================

        valid_contract_types = {
            choice[0]
            for choice in Contract._meta.get_field(
                "type"
            ).choices
        }

        if contract_type not in valid_contract_types:
            messages.error(
                request,
                "Wybierz prawidłowy typ umowy.",
            )
            return redirect(
                "person-details",
                person_id=person_id,
            )

        if not position:
            messages.error(
                request,
                "Podaj stanowisko.",
            )
            return redirect(
                "person-details",
                person_id=person_id,
            )

        date_start = parse_date(
            date_start_raw
        )

        if not date_start:
            messages.error(
                request,
                "Podaj prawidłową datę rozpoczęcia umowy.",
            )
            return redirect(
                "person-details",
                person_id=person_id,
            )

        date_end = None

        if date_end_raw:
            date_end = parse_date(
                date_end_raw
            )

            if not date_end:
                messages.error(
                    request,
                    "Podaj prawidłową datę zakończenia umowy.",
                )
                return redirect(
                    "person-details",
                    person_id=person_id,
                )

            if date_end < date_start:
                messages.error(
                    request,
                    "Data zakończenia nie może być wcześniejsza "
                    "niż data rozpoczęcia.",
                )
                return redirect(
                    "person-details",
                    person_id=person_id,
                )

        salary = None

        if salary_raw:
            try:
                salary = Decimal(
                    salary_raw
                )
            except InvalidOperation:
                messages.error(
                    request,
                    "Podaj prawidłowe wynagrodzenie.",
                )
                return redirect(
                    "person-details",
                    person_id=person_id,
                )

            if salary < 0:
                messages.error(
                    request,
                    "Wynagrodzenie nie może być ujemne.",
                )
                return redirect(
                    "person-details",
                    person_id=person_id,
                )

        # ========================================================
        # CREATE
        # ========================================================

        Contract.objects.create(
            worker=employee,
            type=contract_type,
            position=position,
            date_start=date_start,
            date_end=date_end,
            salary=salary,
            extra_info=extra_info or None,
            first=first,
        )

        messages.success(
            request,
            "Umowa została dodana.",
        )

        return redirect(
            "person-details",
            person_id=person_id,
        )