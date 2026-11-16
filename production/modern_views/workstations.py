from django.contrib.auth.mixins import (
    PermissionRequiredMixin,
)
from django.contrib.auth.mixins import (
    PermissionRequiredMixin,
)
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views import View

from production.services.workstations import (
    finish_production_unit,
    start_production_unit,
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

from django.contrib.auth.mixins import (
    PermissionRequiredMixin,
)
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views import View

from production.services.workstations import (
    start_production_unit,
)

from production.services.workstations import (
    finish_production_unit,
    move_production_unit_down,
    move_production_unit_up,
    plan_production_unit,
    remove_production_unit_from_plan,
    start_production_unit,
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


def workstation_action_response(
    request,
    unit,
):
    if (
        request.headers.get(
            "x-requested-with"
        )
        == "XMLHttpRequest"
    ):
        return JsonResponse({
            "success": True,
            "unit_id": unit.id,
            "station_id":
                unit.work_station_id,
            "status":
                unit.status,
        })

    return redirect(
        "modern_production:workstation-details",
        workstation_id=
            unit.work_station_id,
    )

class StartProductionUnitView(
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
        unit = start_production_unit(
            unit_id=unit_id,
        )

        return workstation_action_response(
            request,
            unit,
        )


class FinishProductionUnitView(
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
        unit = finish_production_unit(
            unit_id=unit_id,
        )

        return workstation_action_response(
            request,
            unit,
        )


class PlanProductionUnitView(
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
        unit = plan_production_unit(
            unit_id=unit_id,
        )

        return workstation_action_response(
            request,
            unit,
        )


class RemoveProductionUnitFromPlanView(
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
        unit = (
            remove_production_unit_from_plan(
                unit_id=unit_id,
            )
        )

        return workstation_action_response(
            request,
            unit,
        )


class MoveProductionUnitUpView(
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
        unit = move_production_unit_up(
            unit_id=unit_id,
        )

        return workstation_action_response(
            request,
            unit,
        )


class MoveProductionUnitDownView(
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
        unit = move_production_unit_down(
            unit_id=unit_id,
        )

        return workstation_action_response(
            request,
            unit,
        )