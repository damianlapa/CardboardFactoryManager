from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Count
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views import View

from production.models import (
    ProductionOrder,
    ProductionUnit,
    WorkStation,
)
from warehousemanager.functions import visit_counter


class ProductionMenu(
    PermissionRequiredMixin,
    View,
):
    permission_required = (
        "production.view_productionorder"
    )

    login_url = reverse_lazy("login")

    template_name = "production/menu.html"

    def get(self, request):
        visit_counter(
            request.user,
            "Production dashboard",
        )

        order_counts = {
            row["status"]: row["count"]
            for row in (
                ProductionOrder.objects
                .values("status")
                .annotate(
                    count=Count("id")
                )
            )
        }

        active_units = (
            ProductionUnit.objects
            .filter(
                status="IN PROGRESS"
            )
            .select_related(
                "production_order",
                "production_order__customer",
                "work_station",
            )
            .prefetch_related(
                "persons",
            )
            .order_by(
                "work_station__name",
                "production_order__id_number",
            )
        )

        planned_units = (
            ProductionUnit.objects
            .filter(
                status="PLANNED"
            )
            .select_related(
                "production_order",
                "production_order__customer",
                "work_station",
            )
            .order_by(
                "work_station__name",
                "order",
            )[:10]
        )

        context = {
            "orders_total":
                ProductionOrder.objects.count(),

            "orders_uncompleted":
                order_counts.get(
                    "UNCOMPLETED",
                    0,
                ),

            "orders_planned":
                order_counts.get(
                    "PLANNED",
                    0,
                ),

            "orders_in_progress":
                active_units.count(),

            "stations_count":
                WorkStation.objects.count(),

            "active_units":
                active_units,

            "planned_units":
                planned_units,
        }

        return render(
            request,
            self.template_name,
            context,
        )