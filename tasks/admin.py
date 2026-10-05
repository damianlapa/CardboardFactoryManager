from django.contrib import admin

from .models import UserTask


@admin.register(UserTask)
class UserTaskAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "user",
        "priority",
        "due_date",
        "completed",
        "created_at",
    )

    list_filter = (
        "completed",
        "priority",
        "user",
    )

    search_fields = (
        "title",
        "description",
        "user__username",
    )