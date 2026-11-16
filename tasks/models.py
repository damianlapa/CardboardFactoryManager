from django.conf import settings
from django.db import models


class UserTask(models.Model):
    PRIORITY_CHOICES = (
        (1, "Niski"),
        (2, "Normalny"),
        (3, "Wysoki"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="user_tasks",
    )

    title = models.CharField(
        max_length=200,
    )

    description = models.TextField(
        blank=True,
    )

    due_date = models.DateField(
        null=True,
        blank=True,
    )

    priority = models.PositiveSmallIntegerField(
        choices=PRIORITY_CHOICES,
        default=2,
    )

    completed = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = [
            "completed",
            "-priority",
            "due_date",
            "-created_at",
        ]

    def __str__(self):
        return self.title