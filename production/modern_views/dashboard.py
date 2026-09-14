import datetime

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Count
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views import View
from django.utils import timezone

from production.models import (
    ProductionOrder,
    ProductionUnit,
    WorkStation,
)
from warehousemanager.functions import visit_counter

from warehouse.models import Order as WarehouseOrder


from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Count
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views import View
from django.utils import timezone

from production.models import (
    ProductionOrder,
    ProductionUnit,
    WorkStation,
)

from warehouse.models import Order as WarehouseOrder
from warehousemanager.functions import visit_counter


class ProductionMenu(
    PermissionRequiredMixin,
    View,
):
    permission_required = (
        "production.view_productionorder"
    )

    login_url = reverse_lazy("login")

    template_name = "production/menu.html"

    def get(self, request):
        visit_counter(
            request.user,
            "Production dashboard",
        )

        def days_since(value, today):
            if not value:
                return None

            if isinstance(value, datetime.datetime):
                value = value.date()

            return (today - value).days

        order_counts = {
            row["status"]: row["count"]
            for row in (
                ProductionOrder.objects
                .values("status")
                .annotate(
                    count=Count("id")
                )
            )
        }

        active_units = list(
            ProductionUnit.objects
            .filter(
                status="IN PROGRESS"
            )
            .select_related(
                "production_order",
                "production_order__customer",
                "work_station",
            )
            .prefetch_related(
                "persons",
            )
            .order_by(
                "work_station__name",
                "production_order__id_number",
            )
        )

        planned_units = list(
            ProductionUnit.objects
            .filter(
                status="PLANNED"
            )
            .select_related(
                "production_order",
                "production_order__customer",
                "work_station",
            )
            .order_by(
                "work_station__name",
                "order",
            )[:10]
        )

        # ===================================================
        # WAREHOUSE ORDERS
        # ===================================================

        today = datetime.datetime.today().date()

        production_id_numbers = {
            unit.production_order.id_number
            for unit in active_units + planned_units
        }

        # ProductionOrder.id_number ma format np.:
        # "TFP 123/26"
        #
        # warehouse.Order:
        # provider = TFP
        # order_id = 123/26

        warehouse_order_numbers = []

        for id_number in production_id_numbers:
            try:
                _, order_number = id_number.rsplit(" ", 1)
                warehouse_order_numbers.append(order_number)
            except ValueError:
                pass

        warehouse_orders = (
            WarehouseOrder.objects
            .filter(
                order_id__in=warehouse_order_numbers
            )
            .select_related(
                "provider",
            )
        )

        warehouse_order_map = {
            f"{order.provider} {order.order_id}": order
            for order in warehouse_orders
        }

        # ===================================================
        # DODAJ INFORMACJE DO JEDNOSTEK
        # ===================================================

        for unit in active_units + planned_units:

            warehouse_order = warehouse_order_map.get(
                unit.production_order.id_number
            )

            unit.warehouse_order = warehouse_order
            unit.days_since_customer_order = None
            unit.days_since_cardboard_delivery = None

            if warehouse_order:

                if warehouse_order.customer_date:
                    unit.days_since_customer_order = days_since(
                        warehouse_order.customer_date,
                        today
                    )

                if warehouse_order.delivery_date:
                    unit.days_since_cardboard_delivery = days_since(
                        warehouse_order.delivery_date,
                        today
                    )

        context = {
            "orders_total":
                ProductionOrder.objects.count(),

            "orders_uncompleted":
                order_counts.get(
                    "UNCOMPLETED",
                    0,
                ),

            "orders_planned":
                order_counts.get(
                    "PLANNED",
                    0,
                ),

            "orders_in_progress":
                len(active_units),

            "stations_count":
                WorkStation.objects.count(),

            "active_units":
                active_units,

            "planned_units":
                planned_units,
        }

        return render(
            request,
            self.template_name,
            context,
        )