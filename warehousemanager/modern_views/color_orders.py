from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect
from django.views import View

from ..forms import ColorOrderForm, ColorOrderItemFormSet
from ..services.color_orders import create_color_order

from decimal import Decimal


class ColorOrderCreateView(LoginRequiredMixin, View):
    login_url = "login"
    template_name = "colors/color_order_create.html"

    def get(self, request):
        return render(
            request,
            self.template_name,
            {
                "form": ColorOrderForm(),
                "formset": ColorOrderItemFormSet(),
            },
        )

    def post(self, request):
        form = ColorOrderForm(request.POST)
        formset = ColorOrderItemFormSet(request.POST)

        if not form.is_valid() or not formset.is_valid():
            return render(
                request,
                self.template_name,
                {
                    "form": form,
                    "formset": formset,
                },
            )

        items = []

        for item_form in formset:
            if not item_form.cleaned_data:
                continue

            if item_form.cleaned_data.get("DELETE"):
                continue

            color = item_form.cleaned_data.get("color")
            quantity_kg = item_form.cleaned_data.get("quantity_kg")
            price_per_kg = item_form.cleaned_data.get("price_per_kg")

            if not color:
                continue

            items.append(
                {
                    "color": color,
                    "quantity_kg": quantity_kg,
                    "price_per_kg": price_per_kg,
                }
            )

        try:
            color_order = create_color_order(
                provider=form.cleaned_data["provider"],
                order_date=form.cleaned_data["order_date"],
                number=form.cleaned_data.get("number"),
                notes=form.cleaned_data.get("notes"),
                items=items,
            )

        except ValidationError as exc:
            form.add_error(None, exc)

            return render(
                request,
                self.template_name,
                {
                    "form": form,
                    "formset": formset,
                },
            )

        messages.success(
            request,
            "Zamówienie farb zostało utworzone.",
        )

        return redirect(
            "color-order-detail",
            pk=color_order.pk,
        )


from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.utils import timezone

from ..models import ColorOrder
from ..services.color_orders import receive_color_order


class ColorOrderDetailView(LoginRequiredMixin, View):
    login_url = "login"
    template_name = "colors/color_order_detail.html"

    def get(self, request, pk):
        color_order = (
            ColorOrder.objects
            .prefetch_related(
                "items__color",
                "items__buckets",
            )
            .get(pk=pk)
        )

        return render(
            request,
            self.template_name,
            {
                "color_order": color_order,
            },
        )


class ColorOrderReceiveView(LoginRequiredMixin, View):
    login_url = "login"

    def post(self, request, pk):
        color_order = get_object_or_404(
            ColorOrder,
            pk=pk,
        )

        buckets_by_item = {}

        for item in color_order.items.all():
            raw_weights = request.POST.getlist(
                f"bucket_{item.id}[]"
            )

            weights = []

            for raw_weight in raw_weights:
                raw_weight = raw_weight.strip().replace(",", ".")

                if not raw_weight:
                    continue

                try:
                    weight = Decimal(raw_weight)
                except Exception:
                    messages.error(
                        request,
                        f"Nieprawidłowa waga wiadra: {raw_weight}"
                    )

                    return redirect(
                        "color-order-detail",
                        pk=color_order.pk,
                    )

                weights.append(weight)

            buckets_by_item[item.id] = weights

        received_date_raw = request.POST.get("received_date")

        received_date = None

        if received_date_raw:
            try:
                received_date = timezone.datetime.strptime(
                    received_date_raw,
                    "%Y-%m-%d",
                ).date()
            except ValueError:
                messages.error(
                    request,
                    "Nieprawidłowa data przyjęcia.",
                )

                return redirect(
                    "color-order-detail",
                    pk=color_order.pk,
                )

        try:
            receive_color_order(
                color_order=color_order,
                buckets_by_item=buckets_by_item,
                received_date=received_date,
            )

        except ValidationError as exc:
            messages.error(
                request,
                str(exc),
            )

            return redirect(
                "color-order-detail",
                pk=color_order.pk,
            )

        messages.success(
            request,
            "Zamówienie farb zostało przyjęte.",
        )

        return redirect(
            "color-order-detail",
            pk=color_order.pk,
        )


from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.shortcuts import render

from ..models import ColorOrder


class ColorOrderListView(LoginRequiredMixin, View):
    login_url = "login"
    template_name = "colors/color_order_list.html"

    def get(self, request):
        status = request.GET.get("status")

        orders = (
            ColorOrder.objects
            .prefetch_related("items")
            .order_by("-order_date", "-id")
        )

        if status in {
            ColorOrder.STATUS_OPEN,
            ColorOrder.STATUS_RECEIVED,
            ColorOrder.STATUS_CANCELLED,
        }:
            orders = orders.filter(status=status)

        return render(
            request,
            self.template_name,
            {
                "orders": orders,
                "selected_status": status,
            },
        )