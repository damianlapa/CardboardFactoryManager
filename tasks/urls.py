from django.urls import path

from tasks.views import (
    TaskListView,
    TaskCreateView,
    TaskUpdateView,
    TaskToggleView,
    TaskDeleteView,
)


app_name = "tasks"


urlpatterns = [
    path(
        "",
        TaskListView.as_view(),
        name="list",
    ),
    path(
        "create/",
        TaskCreateView.as_view(),
        name="create",
    ),
    path(
        "<int:pk>/update/",
        TaskUpdateView.as_view(),
        name="update",
    ),
    path(
        "<int:pk>/toggle/",
        TaskToggleView.as_view(),
        name="toggle",
    ),
    path(
        "<int:pk>/delete/",
        TaskDeleteView.as_view(),
        name="delete",
    ),
]