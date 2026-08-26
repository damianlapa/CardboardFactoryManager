from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import models, transaction
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    DeleteView,
    UpdateView,
)

from production.forms import ProductionUnitForm
from production.models import (
    ProductionOrder,
    ProductionUnit,
)


# ============================================================
# HELPERS
# ============================================================


def get_unit_queryset():
    return (
        ProductionUnit.objects
        .select_related(
            "production_order",
            "production_order__customer",
            "work_station",
            "punch",
            "polymer",
        )
        .prefetch_related(
            "persons",
        )
    )


def redirect_to_unit(unit):
    return redirect(
        "modern_production:unit-details",
        unit_id=unit.id,
    )


def redirect_to_order(unit):
    return redirect(
        "modern_production:production-details",
        production_order_id=
            unit.production_order_id,
    )


def update_production_order_status(
    production_order,
):
    units = (
        ProductionUnit.objects
        .filter(
            production_order=production_order
        )
        .values_list(
            "status",
            flat=True,
        )
    )

    statuses = list(units)

    if not statuses:
        return

    if all(
        status == "FINISHED"
        for status in statuses
    ):
        new_status = "FINISHED"

    elif all(
        status in (
            "FINISHED",
            "PLANNED",
        )
        for status in statuses
    ):
        new_status = "PLANNED"

    else:
        return

    if (
        production_order.status
        != new_status
    ):
        production_order.status = (
            new_status
        )

        production_order.save(
            update_fields=[
                "status",
            ]
        )


# ============================================================
# DETAIL
# ============================================================


class ProductionUnitDetailView(
    PermissionRequiredMixin,
    View,
):
    permission_required = (
        "production.view_productionunit"
    )

    login_url = reverse_lazy(
        "login"
    )

    template_name = (
        "production/units/detail.html"
    )

    def get(
        self,
        request,
        unit_id,
    ):
        unit = get_object_or_404(
            get_unit_queryset(),
            pk=unit_id,
        )

        try:
            duration_minutes = (
                unit.unit_duration_minutes()
            )
        except Exception:
            duration_minutes = None

        try:
            persons_count, person_minutes = (
                unit.duration_person()
            )
        except Exception:
            persons_count = (
                unit.persons.count()
            )

            person_minutes = None

        try:
            pieces_per_hour = (
                unit.pieces_per_hour()
            )
        except Exception:
            pieces_per_hour = None

        context = {
            "unit": unit,

            "duration_minutes":
                duration_minutes,

            "persons_count":
                persons_count,

            "person_minutes":
                person_minutes,

            "pieces_per_hour":
                pieces_per_hour,
        }

        return render(
            request,
            self.template_name,
            context,
        )


# ============================================================
# UPDATE
# ============================================================


class ProductionUnitUpdateView(
    PermissionRequiredMixin,
    UpdateView,
):
    permission_required = (
        "production.change_productionunit"
    )

    login_url = reverse_lazy(
        "login"
    )

    model = ProductionUnit

    form_class = ProductionUnitForm

    template_name = (
        "production/units/form.html"
    )

    def get_queryset(self):
        return get_unit_queryset()

    def get_success_url(self):
        return reverse(
            "modern_production:unit-details",
            kwargs={
                "unit_id":
                    self.object.id,
            },
        )


# ============================================================
# DELETE
# ============================================================


class ProductionUnitDeleteView(
    PermissionRequiredMixin,
    DeleteView,
):
    permission_required = (
        "production.delete_productionunit"
    )

    login_url = reverse_lazy(
        "login"
    )

    model = ProductionUnit

    template_name = (
        "production/units/confirm_delete.html"
    )

    def get_queryset(self):
        return get_unit_queryset()

    def form_valid(self, form):
        self.object = self.get_object()

        production_order_id = (
            self.object.production_order_id
        )

        removed_sequence = (
            self.object.sequence
        )

        with transaction.atomic():
            self.object.delete()

            ProductionUnit.objects.filter(
                production_order_id=
                    production_order_id,
                sequence__gt=
                    removed_sequence,
            ).update(
                sequence=models.F(
                    "sequence"
                ) - 1
            )

        return redirect(
            "modern_production:production-details",
            production_order_id=
                production_order_id,
        )

# ============================================================
# START
# ============================================================


class ProductionUnitStartView(
    PermissionRequiredMixin,
    View,
):
    permission_required = (
        "production.change_productionunit"
    )

    def post(
        self,
        request,
        unit_id,
    ):
        unit = get_object_or_404(
            ProductionUnit,
            pk=unit_id,
        )

        if unit.status == "FINISHED":
            messages.error(
                request,
                "Nie można uruchomić zakończonej operacji.",
            )

            return redirect_to_unit(
                unit
            )

        unit.status = "IN PROGRESS"

        if not unit.start:
            unit.start = timezone.now()

        unit.save(
            update_fields=[
                "status",
                "start",
            ]
        )

        messages.success(
            request,
            "Operacja została uruchomiona.",
        )

        return redirect_to_unit(
            unit
        )


# ============================================================
# FINISH
# ============================================================


class ProductionUnitFinishView(
    PermissionRequiredMixin,
    View,
):
    permission_required = (
        "production.change_productionunit"
    )

    def post(
        self,
        request,
        unit_id,
    ):
        unit = get_object_or_404(
            get_unit_queryset(),
            pk=unit_id,
        )

        unit.status = "FINISHED"

        if not unit.end:
            unit.end = timezone.now()

        unit.save(
            update_fields=[
                "status",
                "end",
            ]
        )

        update_production_order_status(
            unit.production_order
        )

        messages.success(
            request,
            "Operacja została zakończona.",
        )

        return redirect_to_unit(
            unit
        )


# ============================================================
# PLAN
# ============================================================


class ProductionUnitPlanView(
    PermissionRequiredMixin,
    View,
):
    permission_required = (
        "production.change_productionunit"
    )

    def post(
        self,
        request,
        unit_id,
    ):
        unit = get_object_or_404(
            ProductionUnit,
            pk=unit_id,
        )

        if not unit.work_station_id:
            messages.error(
                request,
                "Najpierw wybierz stanowisko.",
            )

            return redirect_to_unit(
                unit
            )

        if unit.status == "FINISHED":
            messages.error(
                request,
                "Zakończonej operacji nie można ponownie planować.",
            )

            return redirect_to_unit(
                unit
            )

        unit.status = "PLANNED"

        unit.order = (
            ProductionUnit.last_in_line(
                unit.work_station
            )
            + 1
        )

        unit.save(
            update_fields=[
                "status",
                "order",
            ]
        )

        update_production_order_status(
            unit.production_order
        )

        messages.success(
            request,
            "Operacja została dodana do kolejki.",
        )

        return redirect_to_unit(
            unit
        )


# ============================================================
# REMOVE FROM PLAN
# ============================================================


class ProductionUnitRemoveFromPlanView(
    PermissionRequiredMixin,
    View,
):
    permission_required = (
        "production.change_productionunit"
    )

    def post(
        self,
        request,
        unit_id,
    ):
        unit = get_object_or_404(
            ProductionUnit,
            pk=unit_id,
        )

        unit.status = "NOT STARTED"
        unit.order = None
        unit.start = None
        unit.end = None

        unit.save(
            update_fields=[
                "status",
                "order",
                "start",
                "end",
            ]
        )

        messages.success(
            request,
            "Operacja została usunięta z planu.",
        )

        return redirect_to_unit(
            unit
        )


# ============================================================
# MOVE UP
# ============================================================


class ProductionUnitMoveUpView(
    PermissionRequiredMixin,
    View,
):
    permission_required = (
        "production.change_productionunit"
    )

    def post(
        self,
        request,
        unit_id,
    ):
        unit = get_object_or_404(
            ProductionUnit,
            pk=unit_id,
        )

        if unit.status != "PLANNED":
            messages.error(
                request,
                "Zmiana kolejności jest dostępna tylko dla zaplanowanych operacji.",
            )

            return redirect_to_unit(
                unit
            )

        unit.move_up_unit()

        messages.success(
            request,
            "Operacja została przesunięta w kolejce.",
        )

        return redirect_to_unit(
            unit
        )


# ============================================================
# MOVE DOWN
# ============================================================


class ProductionUnitMoveDownView(
    PermissionRequiredMixin,
    View,
):
    permission_required = (
        "production.change_productionunit"
    )

    def post(
        self,
        request,
        unit_id,
    ):
        unit = get_object_or_404(
            ProductionUnit,
            pk=unit_id,
        )

        if unit.status != "PLANNED":
            messages.error(
                request,
                "Zmiana kolejności jest dostępna tylko dla zaplanowanych operacji.",
            )

            return redirect_to_unit(
                unit
            )

        unit.move_down_unit()

        messages.success(
            request,
            "Operacja została przesunięta w kolejce.",
        )

        return redirect_to_unit(
            unit
        )
