import datetime

from django.db.models import F
from django.shortcuts import get_object_or_404
from django.utils import timezone

from tasks.models import UserTask


def get_user_tasks(user):
    active_tasks = (
        UserTask.objects
        .filter(
            user=user,
            completed=False,
        )
        .order_by(
            F("due_date").asc(nulls_last=True),
            "-priority",
            "-created_at",
        )
    )

    completed_tasks = (
        UserTask.objects
        .filter(
            user=user,
            completed=True,
        )
        .order_by(
            "-completed_at",
            "-created_at",
        )[:20]
    )

    return active_tasks, completed_tasks


def _clean_task_data(data):
    title = (data.get("title") or "").strip()
    description = (data.get("description") or "").strip()
    due_date = data.get("due_date") or None

    try:
        priority = int(data.get("priority") or 2)
    except (TypeError, ValueError):
        priority = 2

    if priority not in (1, 2, 3):
        priority = 2

    return {
        "title": title,
        "description": description,
        "due_date": due_date,
        "priority": priority,
    }


def create_user_task(user, data):
    task_data = _clean_task_data(data)

    if not task_data["title"]:
        return None

    return UserTask.objects.create(
        user=user,
        **task_data,
    )


def update_user_task(user, task_id, data):
    task = get_object_or_404(
        UserTask,
        id=task_id,
        user=user,
    )

    task_data = _clean_task_data(data)

    if not task_data["title"]:
        return None

    task.title = task_data["title"]
    task.description = task_data["description"]
    task.due_date = task_data["due_date"]
    task.priority = task_data["priority"]

    task.save(
        update_fields=[
            "title",
            "description",
            "due_date",
            "priority",
            "updated_at",
        ]
    )

    return task


def toggle_user_task(user, task_id):
    task = get_object_or_404(
        UserTask,
        id=task_id,
        user=user,
    )

    task.completed = not task.completed
    task.completed_at = timezone.now() if task.completed else None

    task.save(
        update_fields=[
            "completed",
            "completed_at",
            "updated_at",
        ]
    )

    return task


def delete_user_task(user, task_id):
    task = get_object_or_404(
        UserTask,
        id=task_id,
        user=user,
    )

    task.delete()

    return task_id


from django.db.models import F
from django.utils import timezone


def get_user_task_summary(user, limit=5):
    today = datetime.datetime.today()

    queryset = (
        UserTask.objects
        .filter(
            user=user,
            completed=False,
        )
        .order_by(
            F("due_date").asc(nulls_last=True),
            "-priority",
            "-created_at",
        )
    )

    tasks = list(queryset[:limit])

    return {
        "tasks": tasks,
        "count": queryset.count(),
        "overdue_count": queryset.filter(
            due_date__lt=today,
        ).count(),
        "today_count": queryset.filter(
            due_date=today,
        ).count(),
    }


def get_user_open_task_count(user):
    if not user.is_authenticated:
        return 0

    return UserTask.objects.filter(
        user=user,
        completed=False,
    ).count()