import json

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views import View
from django.shortcuts import get_object_or_404

from production.services.staffing import (
    StaffingError,
    assign_worker,
    get_staffing_context,
    unassign_worker,
)

from production.models import (
    ProductionUnit
)


# ============================================================
# STAFFING BOARD
# ============================================================


class ProductionStaffingView(
    PermissionRequiredMixin,
    View,
):
    """
    Główny widok obsady produkcji.

    Lewa strona:
    - pracownicy,
    - kwalifikacje.

    Prawa strona:
    - jednostki produkcyjne,
    - wymagana obsada,
    - aktualnie przypisane osoby.
    """

    permission_required = (
        "production.view_productionunit"
    )

    login_url = reverse_lazy(
        "login"
    )

    template_name = (
        "production/staffing/board.html"
    )

    def get(
        self,
        request,
        *args,
        **kwargs,
    ):
        context = (
            get_staffing_context()
        )

        return render(
            request,
            self.template_name,
            context,
        )


# ============================================================
# ASSIGN WORKER
# ============================================================


class ProductionStaffingAssignView(
    PermissionRequiredMixin,
    View,
):
    """
    AJAX:
    przypisanie pracownika do ProductionUnit.
    """

    permission_required = (
        "production.change_productionunit"
    )

    login_url = reverse_lazy(
        "login"
    )

    def post(
        self,
        request,
        *args,
        **kwargs,
    ):
        try:
            data = json.loads(
                request.body.decode(
                    "utf-8"
                )
            )

        except (
            json.JSONDecodeError,
            UnicodeDecodeError,
        ):
            return JsonResponse(
                {
                    "success": False,
                    "error": (
                        "Nieprawidłowe dane "
                        "żądania."
                    ),
                },
                status=400,
            )


        try:
            unit_id = int(
                data["unit_id"]
            )

            worker_id = int(
                data["worker_id"]
            )

        except (
            KeyError,
            TypeError,
            ValueError,
        ):
            return JsonResponse(
                {
                    "success": False,
                    "error": (
                        "Nie podano poprawnego "
                        "pracownika lub jednostki."
                    ),
                },
                status=400,
            )


        try:
            unit = assign_worker(
                unit_id=unit_id,
                worker_id=worker_id,
            )

        except StaffingError as error:
            return JsonResponse(
                {
                    "success": False,
                    "error": str(error),
                },
                status=400,
            )


        return JsonResponse(
            {
                "success": True,

                "message": (
                    "Pracownik został "
                    "przypisany."
                ),

                "unit_id": unit.id,

                "worker_id": worker_id,
            }
        )


# ============================================================
# UNASSIGN WORKER
# ============================================================


class ProductionStaffingUnassignView(
    PermissionRequiredMixin,
    View,
):
    """
    AJAX:
    usunięcie pracownika z ProductionUnit.
    """

    permission_required = (
        "production.change_productionunit"
    )

    login_url = reverse_lazy(
        "login"
    )

    def post(
        self,
        request,
        *args,
        **kwargs,
    ):
        try:
            data = json.loads(
                request.body.decode(
                    "utf-8"
                )
            )

        except (
            json.JSONDecodeError,
            UnicodeDecodeError,
        ):
            return JsonResponse(
                {
                    "success": False,
                    "error": (
                        "Nieprawidłowe dane "
                        "żądania."
                    ),
                },
                status=400,
            )


        try:
            unit_id = int(
                data["unit_id"]
            )

            worker_id = int(
                data["worker_id"]
            )

        except (
            KeyError,
            TypeError,
            ValueError,
        ):
            return JsonResponse(
                {
                    "success": False,
                    "error": (
                        "Nie podano poprawnego "
                        "pracownika lub jednostki."
                    ),
                },
                status=400,
            )


        try:
            unit = unassign_worker(
                unit_id=unit_id,
                worker_id=worker_id,
            )

        except StaffingError as error:
            return JsonResponse(
                {
                    "success": False,
                    "error": str(error),
                },
                status=400,
            )


        return JsonResponse(
            {
                "success": True,

                "message": (
                    "Pracownik został "
                    "usunięty z operacji."
                ),

                "unit_id": unit.id,

                "worker_id": worker_id,
            }
        )


class ProductionStaffingRequirementsView(
    PermissionRequiredMixin,
    View,
):
    permission_required = (
        "production.change_productionunit"
    )

    login_url = reverse_lazy(
        "login"
    )

    def post(
        self,
        request,
        *args,
        **kwargs,
    ):
        try:
            data = json.loads(
                request.body.decode(
                    "utf-8"
                )
            )

            unit_id = int(
                data["unit_id"]
            )

            field = data["field"]

            delta = int(
                data["delta"]
            )

        except (
            KeyError,
            TypeError,
            ValueError,
            json.JSONDecodeError,
            UnicodeDecodeError,
        ):
            return JsonResponse(
                {
                    "success": False,
                    "error": "Nieprawidłowe dane.",
                },
                status=400,
            )

        if field not in (
            "required_operators",
            "required_helpers",
        ):
            return JsonResponse(
                {
                    "success": False,
                    "error": "Nieprawidłowe pole.",
                },
                status=400,
            )

        unit = get_object_or_404(
            ProductionUnit,
            pk=unit_id,
        )

        current_value = (
            getattr(
                unit,
                field,
            )
            or 0
        )

        new_value = max(
            0,
            current_value + delta,
        )

        setattr(
            unit,
            field,
            new_value,
        )

        unit.save(
            update_fields=[
                field,
            ]
        )

        return JsonResponse(
            {
                "success": True,
                "unit_id": unit.id,
                "field": field,
                "value": new_value,
            }
        )


class ProductionStaffingEstimatedTimeView(
    PermissionRequiredMixin,
    View,
):
    permission_required = (
        "production.change_productionunit"
    )

    login_url = reverse_lazy(
        "login"
    )

    def post(
        self,
        request,
        *args,
        **kwargs,
    ):
        try:
            data = json.loads(
                request.body.decode(
                    "utf-8"
                )
            )

            unit_id = int(
                data["unit_id"]
            )

            estimated_time = int(
                data["estimated_time"]
            )

        except (
            KeyError,
            TypeError,
            ValueError,
            json.JSONDecodeError,
            UnicodeDecodeError,
        ):
            return JsonResponse(
                {
                    "success": False,
                    "error": "Nieprawidłowe dane.",
                },
                status=400,
            )

        if estimated_time <= 0:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Czas musi być większy od 0.",
                },
                status=400,
            )

        unit = get_object_or_404(
            ProductionUnit.objects
            .select_related(
                "production_order"
            )
            .prefetch_related(
                "persons"
            ),
            pk=unit_id,
        )

        unit.estimated_time = (
            estimated_time
        )

        unit.save(
            update_fields=[
                "estimated_time"
            ]
        )

        quantity = (
            unit.production_order.quantity
            or 0
        )

        persons_count = (
            unit.persons.count()
        )

        sheets_per_hour = 0
        sheets_per_person_hour = 0

        if quantity and estimated_time:

            sheets_per_hour = round(
                quantity
                * 60
                / estimated_time
            )

            if persons_count:

                sheets_per_person_hour = round(
                    sheets_per_hour
                    / persons_count
                )

        return JsonResponse(
            {
                "success": True,

                "estimated_time":
                    estimated_time,

                "sheets_per_hour":
                    sheets_per_hour,

                "sheets_per_person_hour":
                    sheets_per_person_hour,

                "persons_count":
                    persons_count,
            }
        )