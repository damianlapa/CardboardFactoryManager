from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import render
from django.views import View
import datetime
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from warehousemanager.functions import visit_counter
from warehousemanager.services.absences import (
    build_calendar_context,
    build_calendar_data,
)

from warehousemanager.models import (
    Absence,
    ExtraHour,
    Person,
)


class ModernAbsenceListView(
    PermissionRequiredMixin,
    View,
):
    permission_required = (
        "warehousemanager.view_absence"
    )

    template_name = (
        "absences/list.html"
    )

    def get(self, request):
        visit_counter(
            request.user,
            "modern_absences",
        )

        context = build_calendar_context(
            user=request.user,
            year=request.GET.get("year"),
            month=request.GET.get("month"),
            contract_type=request.GET.get(
                "contract_type"
            ),
        )

        return render(
            request,
            self.template_name,
            context,
        )


class ModernAbsenceCalendarDataView(
    PermissionRequiredMixin,
    View,
):
    permission_required = (
        "warehousemanager.view_absence"
    )

    def get(self, request):
        data = build_calendar_data(
            user=request.user,
            year=request.GET.get("year"),
            month=request.GET.get("month"),
            contract_type=request.GET.get(
                "contract_type"
            ),
        )

        return JsonResponse(data)


class ModernAbsenceDayUpdateView(
    PermissionRequiredMixin,
    View,
):
    permission_required = "warehousemanager.view_absence"

    def post(self, request):
        worker_id = request.POST.get("worker_id")
        date_raw = request.POST.get("date")

        absence_type = (
            request.POST.get("absence_type") or ""
        ).strip()

        absence_value_raw = (
            request.POST.get("absence_value") or ""
        ).strip()

        additional_info = (
            request.POST.get("additional_info") or ""
        ).strip()

        extra_hours_enabled = (
            request.POST.get("extra_hours_enabled") == "true"
        )

        extra_hours_quantity_raw = (
            request.POST.get("extra_hours_quantity") or ""
        ).strip()

        extra_hours_full_day = (
            request.POST.get("extra_hours_full_day") == "true"
        )

        # -----------------------------------------------------
        # Basic validation
        # -----------------------------------------------------

        try:
            selected_date = datetime.date.fromisoformat(
                date_raw
            )
        except (TypeError, ValueError):
            return JsonResponse(
                {
                    "ok": False,
                    "error": "Nieprawidłowa data.",
                },
                status=400,
            )

        worker = get_object_or_404(
            Person,
            id=worker_id,
        )

        if worker.job_start and selected_date < worker.job_start:
            return JsonResponse(
                {
                    "ok": False,
                    "error": (
                        "Wybrany dzień przypada przed "
                        "rozpoczęciem zatrudnienia."
                    ),
                },
                status=400,
            )

        if worker.job_end and selected_date > worker.job_end:
            return JsonResponse(
                {
                    "ok": False,
                    "error": (
                        "Wybrany dzień przypada po "
                        "zakończeniu zatrudnienia."
                    ),
                },
                status=400,
            )

        # -----------------------------------------------------
        # Permissions
        # -----------------------------------------------------

        existing_absence = (
            Absence.objects
            .filter(
                worker=worker,
                absence_date=selected_date,
            )
            .first()
        )

        existing_extra_hours = (
            ExtraHour.objects
            .filter(
                worker=worker,
                extras_date=selected_date,
            )
            .first()
        )

        wants_absence = bool(absence_type)

        if wants_absence:
            if existing_absence:
                if not request.user.has_perm(
                    "warehousemanager.change_absence"
                ):
                    return JsonResponse(
                        {
                            "ok": False,
                            "error": (
                                "Nie masz uprawnień do "
                                "zmiany nieobecności."
                            ),
                        },
                        status=403,
                    )

            elif not request.user.has_perm(
                "warehousemanager.add_absence"
            ):
                return JsonResponse(
                    {
                        "ok": False,
                        "error": (
                            "Nie masz uprawnień do "
                            "dodawania nieobecności."
                        ),
                    },
                    status=403,
                )

        elif existing_absence:
            if not request.user.has_perm(
                "warehousemanager.delete_absence"
            ):
                return JsonResponse(
                    {
                        "ok": False,
                        "error": (
                            "Nie masz uprawnień do "
                            "usuwania nieobecności."
                        ),
                    },
                    status=403,
                )

        # -----------------------------------------------------
        # Absence-specific validation
        # -----------------------------------------------------

        absence_value = None

        if absence_type == "SP":
            try:
                absence_value = int(absence_value_raw)
            except (TypeError, ValueError):
                return JsonResponse(
                    {
                        "ok": False,
                        "error": (
                            "Podaj liczbę minut spóźnienia."
                        ),
                    },
                    status=400,
                )

            if absence_value <= 0:
                return JsonResponse(
                    {
                        "ok": False,
                        "error": (
                            "Liczba minut spóźnienia "
                            "musi być większa od zera."
                        ),
                    },
                    status=400,
                )

        if absence_type == "IN" and not additional_info:
            return JsonResponse(
                {
                    "ok": False,
                    "error": (
                        "Dla innej nieobecności "
                        "podaj opis."
                    ),
                },
                status=400,
            )

        # -----------------------------------------------------
        # Extra hours validation
        # -----------------------------------------------------

        extra_hours_quantity = None

        if extra_hours_enabled:
            try:
                extra_hours_quantity = Decimal(
                    extra_hours_quantity_raw.replace(",", ".")
                )
            except (InvalidOperation, AttributeError):
                return JsonResponse(
                    {
                        "ok": False,
                        "error": (
                            "Podaj prawidłową liczbę godzin."
                        ),
                    },
                    status=400,
                )

            if extra_hours_quantity <= 0:
                return JsonResponse(
                    {
                        "ok": False,
                        "error": (
                            "Liczba godzin musi być "
                            "większa od zera."
                        ),
                    },
                    status=400,
                )

            if extra_hours_quantity > Decimal("16"):
                return JsonResponse(
                    {
                        "ok": False,
                        "error": (
                            "Liczba dodatkowych godzin "
                            "jest nieprawidłowa."
                        ),
                    },
                    status=400,
                )

        # -----------------------------------------------------
        # Save
        # -----------------------------------------------------

        with transaction.atomic():

            # ABSENCE
            if absence_type:

                absence, _ = (
                    Absence.objects
                    .get_or_create(
                        worker=worker,
                        absence_date=selected_date,
                        defaults={
                            "absence_type": absence_type,
                        },
                    )
                )

                absence.absence_type = absence_type

                if absence_type == "SP":
                    absence.value = absence_value
                else:
                    absence.value = None

                if absence_type == "IN":
                    absence.additional_info = additional_info
                else:
                    absence.additional_info = None

                absence.save()

            else:

                Absence.objects.filter(
                    worker=worker,
                    absence_date=selected_date,
                ).delete()

            # EXTRA HOURS
            if extra_hours_enabled:

                extra_hours, _ = (
                    ExtraHour.objects
                    .get_or_create(
                        worker=worker,
                        extras_date=selected_date,
                        defaults={
                            "quantity": extra_hours_quantity,
                            "full_day": extra_hours_full_day,
                        },
                    )
                )

                extra_hours.quantity = extra_hours_quantity
                extra_hours.full_day = extra_hours_full_day
                extra_hours.save()

            else:

                ExtraHour.objects.filter(
                    worker=worker,
                    extras_date=selected_date,
                ).delete()

        return JsonResponse({
            "ok": True,
        })