import datetime
import json

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View

from production.services.daily_planning import (
    DailyPlanningError,
    create_task_from_unit,
    get_day_planning_context,
    get_task_json,
    move_task,
    remove_task,
)


class CurrentDailyPlanningView(
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
        *args,
        **kwargs,
    ):
        today = datetime.date.today()

        return redirect(
            "modern_production:daily-planning",
            day=today.isoformat(),
        )


class DailyPlanningView(
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
        "production/planning/day.html"
    )

    def get(
        self,
        request,
        day,
        *args,
        **kwargs,
    ):
        try:
            planning_day = (
                datetime.date.fromisoformat(
                    day
                )
            )

        except ValueError:
            return JsonResponse(
                {
                    "success": False,
                    "error":
                        "Nieprawidłowa data.",
                },
                status=400,
            )

        return render(
            request,
            self.template_name,
            get_day_planning_context(
                planning_day
            ),
        )


class DailyPlanningCreateTaskView(
    PermissionRequiredMixin,
    View,
):
    permission_required = (
        "production.change_weeklyplan"
    )

    login_url = reverse_lazy(
        "login"
    )

    def post(
        self,
        request,
        day,
        *args,
        **kwargs,
    ):
        try:
            planning_day = (
                datetime.date.fromisoformat(
                    day
                )
            )

            data = json.loads(
                request.body.decode(
                    "utf-8"
                )
            )

            unit_id = int(
                data["unit_id"]
            )

            station_id = int(
                data["station_id"]
            )

            start_minutes = int(
                data["start_minutes"]
            )

        except (
            ValueError,
            TypeError,
            KeyError,
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

            task = create_task_from_unit(
                day=planning_day,
                unit_id=unit_id,
                station_id=station_id,
                start_minutes=start_minutes,
            )

            task_json = get_task_json(
                task,
                day=planning_day,
            )

        except DailyPlanningError as error:

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
                "task": task_json,
            }
        )


class DailyPlanningMoveTaskView(
    PermissionRequiredMixin,
    View,
):
    permission_required = (
        "production.change_weeklyplan"
    )

    login_url = reverse_lazy(
        "login"
    )

    def post(
        self,
        request,
        day,
        *args,
        **kwargs,
    ):
        try:
            planning_day = (
                datetime.date.fromisoformat(
                    day
                )
            )

            data = json.loads(
                request.body.decode(
                    "utf-8"
                )
            )

            task_id = int(
                data["task_id"]
            )

            station_id = int(
                data["station_id"]
            )

            start_minutes = int(
                data["start_minutes"]
            )

        except (
            ValueError,
            TypeError,
            KeyError,
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

            task = move_task(
                day=planning_day,
                task_id=task_id,
                station_id=station_id,
                start_minutes=start_minutes,
            )

            task_json = get_task_json(
                task,
                day=planning_day,
            )

        except DailyPlanningError as error:

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
                "task": task_json,
            }
        )


class DailyPlanningRemoveTaskView(
    PermissionRequiredMixin,
    View,
):
    permission_required = (
        "production.change_weeklyplan"
    )

    login_url = reverse_lazy(
        "login"
    )

    def post(
        self,
        request,
        day,
        task_id,
        *args,
        **kwargs,
    ):
        try:
            datetime.date.fromisoformat(
                day
            )

        except ValueError:
            return JsonResponse(
                {
                    "success": False,
                    "error":
                        "Nieprawidłowa data.",
                },
                status=400,
            )

        try:

            remove_task(
                task_id=task_id,
            )

        except DailyPlanningError as error:

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
            }
        )