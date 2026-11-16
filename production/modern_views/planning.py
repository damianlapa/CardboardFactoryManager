import datetime
import json

from django.contrib.auth.mixins import (
    PermissionRequiredMixin,
)
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views import View

from production.services.planning import (
    PlanningError,
    get_or_create_weekly_plan,
    get_weekly_plan_context,
    move_task,
    remove_task_from_plan,
)


# ============================================================
# WEEKLY PLAN
# ============================================================


class WeeklyPlanView(
    PermissionRequiredMixin,
    View,
):
    permission_required = (
        "production.view_weeklyplan"
    )

    login_url = reverse_lazy(
        "login"
    )

    template_name = (
        "production/planning/week.html"
    )

    def get(
        self,
        request,
        year,
        week,
    ):
        context = (
            get_weekly_plan_context(
                year=year,
                week=week,
            )
        )

        return render(
            request,
            self.template_name,
            context,
        )


# ============================================================
# MOVE TASK
# ============================================================


class WeeklyPlanMoveTaskView(
    PermissionRequiredMixin,
    View,
):
    permission_required = (
        "production.change_weeklyplan"
    )

    def post(
        self,
        request,
        year,
        week,
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
                    "error":
                        "Nieprawidłowe dane.",
                },
                status=400,
            )

        try:

            plan = (
                get_or_create_weekly_plan(
                    year=year,
                    week=week,
                )
            )

            target_station_id = int(
                data.get(
                    "station_id"
                )
            )

            target_day = (
                datetime.date.fromisoformat(
                    data.get(
                        "date"
                    )
                )
            )

            target_index = int(
                data.get(
                    "index",
                    0,
                )
            )

            task_id = data.get(
                "task_id"
            )

            unit_id = data.get(
                "unit_id"
            )

            if task_id is not None:
                task_id = int(
                    task_id
                )

            if unit_id is not None:
                unit_id = int(
                    unit_id
                )

            task = move_task(
                plan=plan,

                task_id=task_id,
                unit_id=unit_id,

                target_station_id=
                    target_station_id,

                target_day=
                    target_day,

                target_index=
                    target_index,
            )

            return JsonResponse({
                "success": True,

                "task_id":
                    task.id,

                "unit_id":
                    task.production_unit_id,
            })


        except (
            TypeError,
            ValueError,
        ):
            return JsonResponse(
                {
                    "success": False,
                    "error":
                        "Nieprawidłowe parametry.",
                },
                status=400,
            )

        except PlanningError as error:

            return JsonResponse(
                {
                    "success": False,
                    "error": str(error),
                },
                status=400,
            )


# ============================================================
# REMOVE TASK
# ============================================================


class WeeklyPlanRemoveTaskView(
    PermissionRequiredMixin,
    View,
):
    permission_required = (
        "production.change_weeklyplan"
    )

    def post(
        self,
        request,
        year,
        week,
        task_id,
    ):
        try:

            plan = (
                get_or_create_weekly_plan(
                    year=year,
                    week=week,
                )
            )

            remove_task_from_plan(
                plan=plan,
                task_id=task_id,
            )

            return JsonResponse({
                "success": True,
            })

        except PlanningError as error:

            return JsonResponse(
                {
                    "success": False,
                    "error": str(error),
                },
                status=400,
            )


class CurrentWeeklyPlanView(
    PermissionRequiredMixin,
    View,
):
    permission_required = (
        "production.view_weeklyplan"
    )

    login_url = reverse_lazy(
        "login"
    )

    def get(
        self,
        request,
    ):
        from django.shortcuts import redirect

        today = datetime.date.today()

        iso = today.isocalendar()

        return redirect(
            "modern_production:weekly-plan",
            year=iso.year,
            week=iso.week,
        )