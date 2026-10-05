from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views import View

from tasks.services.tasks import (
    get_user_tasks,
    create_user_task,
    update_user_task,
    toggle_user_task,
    delete_user_task,
)


class TaskListView(LoginRequiredMixin, View):
    login_url = "login"

    def get(self, request):
        tasks, completed_tasks = get_user_tasks(
            request.user
        )

        return render(
            request,
            "tasks/list.html",
            {
                "tasks": tasks,
                "completed_tasks": completed_tasks,
            },
        )


class TaskCreateView(LoginRequiredMixin, View):
    login_url = "login"

    def post(self, request):
        create_user_task(
            request.user,
            request.POST,
        )

        return redirect("tasks:list")


class TaskUpdateView(LoginRequiredMixin, View):
    login_url = "login"

    def post(self, request, pk):
        task = update_user_task(
            request.user,
            pk,
            request.POST,
        )

        if not task:
            return JsonResponse(
                {
                    "ok": False,
                    "error": "Tytuł zadania jest wymagany.",
                },
                status=400,
            )

        return JsonResponse({
            "ok": True,
            "task": {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "due_date": (
                    task.due_date
                    if task.due_date
                    else ""
                ),
                "due_date_display": (
                    task.due_date
                    if task.due_date
                    else ""
                ),
                "priority": task.priority,
                "priority_display": task.get_priority_display(),
            },
        })


class TaskToggleView(LoginRequiredMixin, View):
    login_url = "login"

    def post(self, request, pk):
        task = toggle_user_task(
            request.user,
            pk,
        )

        return JsonResponse({
            "ok": True,
            "task_id": task.id,
            "completed": task.completed,
            "completed_at": (
                task.completed_at.strftime("%d.%m.%Y %H:%M")
                if task.completed_at
                else None
            ),
            "priority": task.priority,
        })


class TaskDeleteView(LoginRequiredMixin, View):
    login_url = "login"

    def post(self, request, pk):
        task_id = delete_user_task(
            request.user,
            pk,
        )

        return JsonResponse({
            "ok": True,
            "task_id": task_id,
        })