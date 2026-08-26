from django.contrib.auth.mixins import (
    PermissionRequiredMixin,
)
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views import View

from production.services.workstations import (
    get_workstation_detail_context,
    get_workstations_context,
)
from warehousemanager.functions import (
    visit_counter,
)


class WorkStationListView(
    PermissionRequiredMixin,
    View,
):
    permission_required = (
        "production.view_workstation"
    )

    login_url = reverse_lazy(
        "login"
    )

    template_name = (
        "production/workstations/list.html"
    )

    def get(self, request):
        visit_counter(
            request.user,
            "Production Workstations",
        )

        context = (
            get_workstations_context()
        )

        return render(
            request,
            self.template_name,
            context,
        )


class WorkStationDetailView(
    PermissionRequiredMixin,
    View,
):
    permission_required = (
        "production.view_workstation"
    )

    login_url = reverse_lazy(
        "login"
    )

    template_name = (
        "production/workstations/detail.html"
    )

    def get(
        self,
        request,
        workstation_id,
    ):
        context = (
            get_workstation_detail_context(
                workstation_id=
                    workstation_id,
            )
        )

        visit_counter(
            request.user,
            (
                f"{context['station']} "
                "- details"
            ),
        )

        return render(
            request,
            self.template_name,
            context,
        )