import datetime

from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView,
    UpdateView,
)

from production.forms import (
    ProductionOrderForm,
    ProductionUnitForm,
)
from production.models import (
    PRODUCTION_ORDER_STATUSES,
    PRODUCTION_UNIT_STATUSES,
    ProductionOrder,
    ProductionUnit,
    WorkStation,
)
from production.services.orders import (
    get_production_order_detail_context,
)
from warehouse.models import (
    Order,
    Provider,
)
from warehousemanager.functions import visit_counter
from warehousemanager.models import (
    Person,
    Photopolymer,
    Punch,
)


# ============================================================
# ORDER LIST
# ============================================================


class AllProductionOrders(
    PermissionRequiredMixin,
    View,
):
    permission_required = (
        "production.view_productionorder"
    )

    login_url = reverse_lazy("login")

    template_name = (
        "production/orders/list.html"
    )

    ACTIVE_STATUSES = (
        "ORDERED",
        "UNCOMPLETED",
        "COMPLETED",
        "PLANNED",
    )

    def get(self, request):
        visit_counter(
            request.user,
            "All Production Orders",
        )

        search = (
            request.GET.get(
                "q",
                ""
            )
            .strip()
        )

        status = (
            request.GET.get(
                "status",
                ""
            )
            .strip()
        )

        orders = (
            ProductionOrder.objects
            .select_related(
                "customer",
                "photopolymer",
                "punch",
            )
            .annotate(
                units_count=Count(
                    "productionunit",
                    distinct=True,
                )
            )
            .order_by(
                "-priority",
                "-add_date",
            )
        )

        if not status:
            orders = orders.filter(
                status__in=
                    self.ACTIVE_STATUSES
            )

        elif status != "ALL":
            orders = orders.filter(
                status=status
            )

        if search:
            orders = orders.filter(
                Q(
                    id_number__icontains=search
                )
                | Q(
                    customer__name__icontains=search
                )
                | Q(
                    dimensions__icontains=search
                )
                | Q(
                    cardboard__icontains=search
                )
                | Q(
                    cardboard_dimensions__icontains=search
                )
            )

        context = {
            "production_orders":
                orders,

            "orders_count":
                orders.count(),

            "search":
                search,

            "selected_status":
                status,

            "statuses": [
                (
                    "ALL",
                    "Wszystkie",
                ),
                (
                    "UNCOMPLETED",
                    "Niekompletne",
                ),
                (
                    "COMPLETED",
                    "Kompletne",
                ),
                (
                    "PLANNED",
                    "Zaplanowane",
                ),
                (
                    "ORDERED",
                    "Zamówione",
                ),
                (
                    "FINISHED",
                    "Zakończone",
                ),
                (
                    "ARCHIVED",
                    "Archiwalne",
                ),
            ],
        }

        return render(
            request,
            self.template_name,
            context,
        )


# ============================================================
# ORDER DETAIL
# ============================================================


class ProductionOrderDetailView(
    PermissionRequiredMixin,
    View,
):
    permission_required = (
        "production.view_productionorder"
    )

    login_url = reverse_lazy(
        "login"
    )

    template_name = (
        "production/orders/detail.html"
    )

    def get(
        self,
        request,
        production_order_id,
    ):
        context = (
            get_production_order_detail_context(
                production_order_id=
                    production_order_id,
            )
        )

        return render(
            request,
            self.template_name,
            context,
        )

    def post(
        self,
        request,
        production_order_id,
    ):
        if not request.user.has_perm(
            "production.add_productionunit"
        ):
            raise PermissionDenied

        context = (
            get_production_order_detail_context(
                production_order_id=
                    production_order_id,
            )
        )

        production_order = (
            context["production_order"]
        )

        form = ProductionUnitForm(
            request.POST
        )

        if form.is_valid():
            unit = form.save(
                commit=False
            )

            unit.production_order = (
                production_order
            )

            unit.save()

            form.save_m2m()

            return redirect(
                "modern_production:production-details",
                production_order_id=
                    production_order.id,
            )

        context["form"] = form

        return render(
            request,
            self.template_name,
            context,
        )


# ============================================================
# CREATE ORDER
# ============================================================


class ProductionOrderCreateView(
    PermissionRequiredMixin,
    CreateView,
):
    permission_required = (
        "production.add_productionorder"
    )

    login_url = reverse_lazy(
        "login"
    )

    model = ProductionOrder

    form_class = ProductionOrderForm

    template_name = (
        "production/orders/form.html"
    )

    def get_success_url(self):
        return reverse(
            "modern_production:production-details",
            kwargs={
                "production_order_id":
                    self.object.id,
            },
        )


# ============================================================
# UPDATE ORDER
# ============================================================


class ProductionOrderUpdateView(
    PermissionRequiredMixin,
    UpdateView,
):
    permission_required = (
        "production.change_productionorder"
    )

    login_url = reverse_lazy(
        "login"
    )

    model = ProductionOrder

    form_class = ProductionOrderForm

    template_name = (
        "production/orders/form.html"
    )

    def get_success_url(self):
        return reverse(
            "modern_production:production-details",
            kwargs={
                "production_order_id":
                    self.object.id,
            },
        )


# ============================================================
# CHANGE ORDER STATUS
# ============================================================


class ChangeProductionStatus(
    PermissionRequiredMixin,
    View,
):
    permission_required = (
        "production.change_productionorder"
    )

    def post(
        self,
        request,
        production_order_id,
    ):
        production_order = (
            get_object_or_404(
                ProductionOrder,
                pk=production_order_id,
            )
        )

        status = request.POST.get(
            "status"
        )

        allowed_statuses = {
            value
            for value, label
            in PRODUCTION_ORDER_STATUSES
        }

        if status not in allowed_statuses:
            return JsonResponse(
                {
                    "success": False,
                    "error":
                        "Nieprawidłowy status.",
                },
                status=400,
            )

        production_order.status = (
            status
        )

        production_order.save(
            update_fields=[
                "status",
            ]
        )

        return JsonResponse({
            "success": True,
            "status":
                production_order.status,
        })


# ============================================================
# INLINE UNIT UPDATE
# ============================================================


class UpdateProductionUnitInline(
    PermissionRequiredMixin,
    View,
):
    permission_required = (
        "production.change_productionunit"
    )

    INTEGER_NULLABLE_FIELDS = {
        "quantity_start",
        "quantity_end",
        "estimated_time",
    }

    DATETIME_FIELDS = {
        "start",
        "end",
    }

    ALLOWED_FIELDS = {
        "sequence",
        "status",
        "work_station",
        "start",
        "end",
        "quantity_start",
        "quantity_end",
        "estimated_time",
    }

    def post(
        self,
        request,
        unit_id,
    ):
        unit = get_object_or_404(
            ProductionUnit,
            pk=unit_id,
        )

        field = request.POST.get(
            "field"
        )

        value = request.POST.get(
            "value",
            "",
        )

        if field not in self.ALLOWED_FIELDS:
            return JsonResponse(
                {
                    "success": False,
                    "error":
                        "Niedozwolone pole.",
                },
                status=400,
            )

        try:

            # --------------------------------------------
            # WORK STATION
            # --------------------------------------------

            if field == "work_station":
                if not value:
                    raise ValueError(
                        "Stanowisko jest wymagane."
                    )

                unit.work_station = (
                    get_object_or_404(
                        WorkStation,
                        pk=int(value),
                    )
                )


            # --------------------------------------------
            # SEQUENCE
            # --------------------------------------------

            elif field == "sequence":
                if not value:
                    raise ValueError(
                        "Kolejność jest wymagana."
                    )

                sequence = int(value)

                if sequence <= 0:
                    raise ValueError(
                        "Kolejność musi być większa od zera."
                    )

                unit.sequence = sequence


            # --------------------------------------------
            # NULLABLE INTEGERS
            # --------------------------------------------

            elif field in self.INTEGER_NULLABLE_FIELDS:
                setattr(
                    unit,
                    field,
                    int(value)
                    if value
                    else None,
                )


            # --------------------------------------------
            # DATETIME
            # --------------------------------------------

            elif field in self.DATETIME_FIELDS:

                if value:
                    dt = datetime.datetime.strptime(
                        value,
                        "%Y-%m-%d %H:%M",
                    )

                    if timezone.is_naive(dt):
                        dt = timezone.make_aware(
                            dt,
                            timezone.get_current_timezone(),
                        )

                    setattr(
                        unit,
                        field,
                        dt,
                    )

                else:
                    setattr(
                        unit,
                        field,
                        None,
                    )


            # --------------------------------------------
            # STATUS
            # --------------------------------------------

            elif field == "status":
                allowed_statuses = {
                    status_value
                    for status_value, label
                    in PRODUCTION_UNIT_STATUSES
                }

                if value not in allowed_statuses:
                    raise ValueError(
                        "Nieprawidłowy status."
                    )

                unit.status = value


            unit.save()

            return JsonResponse({
                "success": True,
                "field": field,
                "value": value,
            })

        except (
            TypeError,
            ValueError,
        ) as error:

            return JsonResponse(
                {
                    "success": False,
                    "error": str(error),
                },
                status=400,
            )


# ============================================================
# UPDATE UNIT PERSONS
# ============================================================


class UpdateProductionUnitPersons(
    PermissionRequiredMixin,
    View,
):
    permission_required = (
        "production.change_productionunit"
    )

    def post(
        self,
        request,
        unit_id,
    ):
        unit = get_object_or_404(
            ProductionUnit,
            pk=unit_id,
        )

        raw_ids = request.POST.getlist(
            "persons[]"
        )

        person_ids = []

        for value in raw_ids:
            try:
                person_ids.append(
                    int(value)
                )
            except (
                TypeError,
                ValueError,
            ):
                continue

        persons = (
            Person.objects
            .filter(
                id__in=person_ids
            )
            .order_by(
                "last_name",
                "first_name",
            )
        )

        unit.persons.set(
            persons
        )

        return JsonResponse({
            "success": True,
            "persons": [
                str(person)
                for person in persons
            ],
        })


# ============================================================
# UPDATE ORDER TOOL
# ============================================================


class UpdateProductionOrderToolView(
    PermissionRequiredMixin,
    View,
):
    permission_required = (
        "production.change_productionorder"
    )

    def post(
        self,
        request,
        production_order_id,
    ):
        production_order = (
            get_object_or_404(
                ProductionOrder,
                pk=production_order_id,
            )
        )

        tool_type = request.POST.get(
            "tool_type"
        )

        tool_id = (
            request.POST.get(
                "tool_id"
            )
            or None
        )

        if tool_type == "punch":

            punch = None

            if tool_id:
                punch = get_object_or_404(
                    Punch,
                    pk=tool_id,
                    active=True,
                )

            production_order.punch = (
                punch
            )

            production_order.save(
                update_fields=[
                    "punch",
                ]
            )

            messages.success(
                request,
                "Wykrojnik został zapisany.",
            )


        elif tool_type == "photopolymer":

            photopolymer = None

            if tool_id:
                photopolymer = (
                    get_object_or_404(
                        Photopolymer,
                        pk=tool_id,
                        active=True,
                    )
                )

            production_order.photopolymer = (
                photopolymer
            )

            production_order.save(
                update_fields=[
                    "photopolymer",
                ]
            )

            messages.success(
                request,
                "Polimer został zapisany.",
            )


        else:

            messages.error(
                request,
                "Nieprawidłowy typ narzędzia.",
            )

        return redirect(
            "modern_production:production-details",
            production_order_id=
                production_order.id,
        )


# ============================================================
# WAREHOUSE ORDER REDIRECT
# ============================================================


class OrderDetailsRedirect(
    PermissionRequiredMixin,
    View,
):
    permission_required = (
        "production.view_productionorder"
    )

    def get(
        self,
        request,
        production_order_id,
    ):
        production_order = (
            get_object_or_404(
                ProductionOrder,
                pk=production_order_id,
            )
        )

        try:
            provider_name, order_number = (
                production_order
                .id_number
                .split(
                    " ",
                    1,
                )
            )

            number, year = (
                order_number.split(
                    "/",
                    1,
                )
            )

            provider = (
                Provider.objects.get(
                    name=provider_name
                )
            )

            order = Order.objects.get(
                provider=provider,
                order_id=f"{number}/{year}",
                order_year=f"20{year}",
            )

        except (
            ValueError,
            Provider.DoesNotExist,
            Order.DoesNotExist,
        ):

            messages.error(
                request,
                "Nie znaleziono odpowiadającego zlecenia magazynowego.",
            )

            return redirect(
                "modern_production:production-details",
                production_order_id=
                    production_order.id,
            )

        return redirect(
            "warehouse:order-detail-view",
            order_id=order.id,
        )