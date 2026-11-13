from urllib.parse import urlencode

from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from warehouse.models import ShipmentItem, ShipmentUnit, ShipmentUnitHistory


class ShipmentItemQuantityForm(forms.Form):
    item_id = forms.IntegerField(min_value=1)
    expected_quantity = forms.IntegerField(min_value=0)
    quantity = forms.IntegerField(
        min_value=1,
        max_value=2147483647,
        error_messages={
            "required": "Wpisz liczbę sztuk.",
            "invalid": "Wpisz całkowitą liczbę sztuk.",
            "min_value": "Liczba sztuk musi być większa od zera.",
            "max_value": "Liczba sztuk jest zbyt duża.",
        },
    )


class ShipmentItemQuantityListView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Ręczna korekta wszystkich pozycji wysyłek, również potwierdzonych."""

    permission_required = "warehouse.change_shipmentunit"
    template_name = "warehouse/shipment_item_quantity_list.html"
    page_size = 50

    def get(self, request):
        search = request.GET.get("q", "").strip()
        shipment_id = request.GET.get("shipment", "").strip()
        only_one = request.GET.get("only_one") == "1"
        items = ShipmentItem.objects.select_related(
            "shipment", "shipment_unit", "shipment_unit__customer",
            "shipment_unit__product", "shipment_unit__palette",
            "shipment_unit__order", "shipment_unit__order__customer",
            "shipment_unit__order__product", "shipment_unit__order__provider",
            "scanned_by",
        ).order_by("-scanned_at", "-id")
        if search:
            matches = (
                Q(shipment_unit__customer__name__icontains=search)
                | Q(shipment_unit__customer__isnull=True,
                    shipment_unit__order__customer__name__icontains=search)
                | Q(shipment_unit__product__alter_name__icontains=search)
                | Q(shipment_unit__product__name__icontains=search)
                | Q(shipment_unit__order__product__alter_name__icontains=search)
                | Q(shipment_unit__order__order_id__icontains=search)
                | Q(shipment_unit__order__name__icontains=search)
            )
            if search.isascii() and search.isdigit() and len(search) <= 18:
                matches |= Q(pk=int(search)) | Q(shipment_id=int(search)) | Q(shipment_unit_id=int(search)) | Q(shipment_unit__order_id=int(search))
            items = items.filter(matches)
        if shipment_id:
            if shipment_id.isascii() and shipment_id.isdigit() and len(shipment_id) <= 18:
                items = items.filter(shipment_id=int(shipment_id))
            else:
                items = items.none()
        if only_one:
            items = items.filter(shipment_unit__quantity=1)
        page_obj = Paginator(items, self.page_size).get_page(request.GET.get("page"))
        params = {"q": search, "shipment": shipment_id}
        if only_one:
            params["only_one"] = "1"
        return render(request, self.template_name, {
            "page_obj": page_obj,
            "search": search,
            "shipment_filter": shipment_id,
            "only_one": only_one,
            "filter_query": urlencode(params),
        })

    def post(self, request):
        form = ShipmentItemQuantityForm(request.POST)
        if not form.is_valid():
            return self.respond(request, {
                "ok": False,
                "message": " ".join(str(error) for errors in form.errors.values() for error in errors),
            }, status=400)
        item_id = form.cleaned_data["item_id"]
        quantity = form.cleaned_data["quantity"]
        expected = form.cleaned_data["expected_quantity"]
        with transaction.atomic():
            # Lock base rows separately: no FOR UPDATE on nullable joins.
            item = get_object_or_404(ShipmentItem.objects.select_for_update(), pk=item_id)
            unit = get_object_or_404(ShipmentUnit.objects.select_for_update(), pk=item.shipment_unit_id)
            if unit.quantity != expected:
                return self.respond(request, {
                    "ok": False,
                    "message": f"Ilość została już zmieniona. Aktualnie: {unit.quantity} szt. Odśwież stronę przed kolejną zmianą.",
                }, status=409)
            if unit.quantity == quantity:
                result = {"ok": True, "message": "Bez zmian.", "quantity": quantity, "changed": False}
            else:
                ShipmentUnitHistory.objects.create(
                    shipment_unit=unit,
                    shipment_unit_original_id=unit.pk,
                    order_id=unit.order_id,
                    product_id=unit.product_id,
                    palette_id=unit.palette_id,
                    quantity=unit.quantity,
                    palette_quantity=unit.palette_quantity,
                    action=ShipmentUnitHistory.ACTION_UPDATE,
                    changed_by=request.user,
                )
                # Explicitly change only quantity of this one locked unit.
                ShipmentUnit.objects.filter(pk=unit.pk).update(quantity=quantity)
                result = {
                    "ok": True, "changed": True, "quantity": quantity,
                    "message": f"Zapisano {quantity} szt. w jednostce #{unit.pk}.",
                }
        return self.respond(request, result)

    def respond(self, request, payload, status=200):
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(payload, status=status)
        if payload["ok"]:
            messages.success(request, payload["message"])
        else:
            messages.error(request, payload["message"])
        # Preserve only known filter parameters; never redirect to user URLs.
        params = {key: request.POST.get(key, "") for key in ("q", "shipment", "only_one", "page")}
        return redirect(reverse("warehouse:shipment-item-quantity-list") + "?" + urlencode(params))
