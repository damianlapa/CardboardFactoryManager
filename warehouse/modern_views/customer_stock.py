from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.views import View

from warehouse.models import CustomerStockList
from warehouse.services.customer_stock import (
    add_customer_stock_item,
    get_customer_stock_context,
)


class CustomerStockListView(LoginRequiredMixin, View):
    login_url = "login"
    template_name = "warehouse/modern/customer_stock/list.html"

    def get_stock_list(self, request):
        stock_list, _ = CustomerStockList.objects.get_or_create(
            user=request.user
        )
        return stock_list

    def get(self, request):
        context = get_customer_stock_context(
            user=request.user
        )

        return render(
            request,
            self.template_name,
            context,
        )

    def post(self, request):
        stock_list = self.get_stock_list(request)

        action = request.POST.get("action")

        if action == "add":
            try:
                add_customer_stock_item(
                    stock_list=stock_list,
                    warehouse_stock_id=request.POST.get("warehouse_stock"),
                    minimum_quantity=request.POST.get("minimum_quantity"),
                )

                messages.success(
                    request,
                    "Stan magazynowy został dodany.",
                )

            except ValidationError as e:
                messages.error(
                    request,
                    e.message,
                )

            except Exception as e:
                messages.error(
                    request,
                    f"Nie udało się dodać pozycji: {e}",
                )

        return redirect(
            "modern_warehouse:customer-stock-list"
        )