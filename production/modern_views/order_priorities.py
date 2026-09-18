import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View

from production.models import ProductionOrder
from production.services.priorities import (
    set_production_order_priority,
)


class ProductionOrderPriorityUpdateView(
    LoginRequiredMixin,
    View,
):
    login_url = "login"

    def post(self, request, production_order_id):

        order = get_object_or_404(
            ProductionOrder,
            pk=production_order_id,
        )

        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse(
                {
                    "ok": False,
                    "error": "Nieprawidłowe dane JSON.",
                },
                status=400,
            )

        try:
            result = set_production_order_priority(
                order=order,
                priority=payload.get("priority"),
                priority_date=payload.get("priority_date"),
                changed_by=request.user,
            )

        except ValidationError as exc:
            return JsonResponse(
                {
                    "ok": False,
                    "error": exc.messages[0],
                },
                status=400,
            )

        order = result["order"]
        history = result["history"]

        return JsonResponse({
            "ok": True,
            "changed": result["changed"],

            "priority": order.priority,

            "priority_label": (
                order.get_priority_display()
                if order.priority
                else None
            ),

            "priority_date": (
                order.priority_date.isoformat()
                if order.priority_date
                else None
            ),

            "priority_date_display": (
                order.priority_date.strftime("%d.%m.%Y")
                if order.priority_date
                else None
            ),

            "changed_by": (
                request.user.get_full_name()
                or request.user.get_username()
            ),

            "changed_at": (
                history.changed_at.strftime("%d.%m.%Y %H:%M")
                if history
                else None
            ),
        })