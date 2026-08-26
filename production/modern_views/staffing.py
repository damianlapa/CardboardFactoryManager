import json

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views import View

from production.services.staffing import (
    StaffingError,
    assign_worker,
    get_staffing_context,
    unassign_worker,
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
