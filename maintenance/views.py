from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, get_object_or_404
from django.views import View
from django.db.models import Prefetch, Sum
from django.db.models import Q


from .models import (
    Machine,
    MachinePart,
    MachinePartAssignment,
    MaintenanceEvent,
    MaintenanceSupplier,
    MaintenanceSupplierContact,
    PartCategory,
)
from warehouse.models import WarehouseStock


class MachineListView(LoginRequiredMixin, View):
    login_url = "login"

    def get(self, request):
        machines = (
            Machine.objects
            .filter(is_active=True)
            .order_by("code", "name")
        )
        return render(request, "maintenance/machine_list.html", locals())


class MachineDetailView(LoginRequiredMixin, View):
    login_url = "login"

    def get(self, request, machine_id):
        machine = get_object_or_404(
            Machine.objects.prefetch_related(
                Prefetch(
                    "part_assignments",
                    queryset=MachinePartAssignment.objects.select_related(
                        "part",
                        "part__category",
                        "part__supplier",
                        "part__stock",
                    ).prefetch_related(
                        "part__stock__warehouse_stocks__warehouse"
                    ).order_by("part__name")
                ),
                Prefetch(
                    "events",
                    queryset=MaintenanceEvent.objects.select_related(
                        "created_by"
                    ).prefetch_related(
                        "parts_used__part",
                        "parts_used__warehouse_stock__warehouse",
                    ).order_by("-date", "-id")
                )
            ),
            id=machine_id
        )

        assignments = machine.part_assignments.all()
        events = machine.events.all()

        critical_parts = [a for a in assignments if a.is_critical]
        missing_parts = []
        low_parts = []

        for assignment in assignments:
            part = assignment.part
            current_qty = part.current_quantity()

            assignment.current_qty = current_qty
            assignment.missing_qty = max(assignment.quantity_needed - current_qty, 0)

            if current_qty <= 0:
                missing_parts.append(assignment)
            elif current_qty < part.min_quantity:
                low_parts.append(assignment)

        return render(request, "maintenance/machine_detail.html", locals())


class PartListView(LoginRequiredMixin, View):
    login_url = "login"

    def get(self, request):
        q = (request.GET.get("q") or "").strip()
        supplier_id = request.GET.get("supplier")
        category_id = request.GET.get("category")
        low_only = request.GET.get("low")

        parts = (
            MachinePart.objects
            .select_related("category", "supplier", "stock")
            .prefetch_related("stock__warehouse_stocks__warehouse")
            .filter(is_active=True)
            .order_by("name", "code")
        )

        if q:
            parts = parts.filter(
                Q(name__icontains=q) |
                Q(code__icontains=q) |
                Q(producer__icontains=q)
            )
        if supplier_id:
            parts = parts.filter(supplier_id=supplier_id)

        if category_id:
            parts = parts.filter(category_id=category_id)

        parts = list(parts)

        for part in parts:
            part.current_qty = part.current_quantity()
            part.below_minimum = part.is_below_minimum()

        if low_only:
            parts = [p for p in parts if p.below_minimum]

        suppliers = MaintenanceSupplier.objects.filter(is_active=True).order_by("name")

        categories = PartCategory.objects.all().order_by("name")

        return render(request, "maintenance/part_list.html", locals())


class PartDetailView(LoginRequiredMixin, View):
    login_url = "login"

    def get(self, request, part_id):
        part = get_object_or_404(
            MachinePart.objects.select_related(
                "category",
                "supplier",
                "stock",
            ).prefetch_related(
                "stock__warehouse_stocks__warehouse",
                "machine_assignments__machine",
                "usages__event__machine",
                "usages__warehouse_stock__warehouse",
            ),
            id=part_id
        )

        current_qty = part.current_quantity()
        below_minimum = part.is_below_minimum()

        warehouse_stocks = []
        if part.stock_id:
            warehouse_stocks = part.stock.warehouse_stocks.all().order_by("warehouse__name")

        machines = part.machine_assignments.all().order_by("machine__code")
        usages = part.usages.all().order_by("-event__date", "-id")

        return render(request, "maintenance/part_detail.html", locals())


class SupplierListView(LoginRequiredMixin, View):
    login_url = "login"

    def get(self, request):
        suppliers = (
            MaintenanceSupplier.objects
            .filter(is_active=True)
            .prefetch_related("contacts", "parts")
            .order_by("name")
        )
        return render(request, "maintenance/supplier_list.html", locals())


class SupplierDetailView(LoginRequiredMixin, View):
    login_url = "login"

    def get(self, request, supplier_id):
        supplier = get_object_or_404(
            MaintenanceSupplier.objects.prefetch_related(
                Prefetch(
                    "contacts",
                    queryset=MaintenanceSupplierContact.objects.order_by("-is_main", "name")
                ),
                Prefetch(
                    "parts",
                    queryset=MachinePart.objects.select_related(
                        "category",
                        "stock",
                    ).prefetch_related(
                        "stock__warehouse_stocks__warehouse"
                    ).order_by("name", "code")
                )
            ),
            id=supplier_id
        )

        contacts = supplier.contacts.all()
        parts = list(supplier.parts.all())

        for part in parts:
            part.current_qty = part.current_quantity()
            part.below_minimum = part.is_below_minimum()

        main_contact = supplier.main_contact()

        return render(request, "maintenance/supplier_detail.html", locals())


class MaintenanceDashboardView(LoginRequiredMixin, View):
    login_url = "login"

    def get(self, request):
        machines_count = Machine.objects.filter(is_active=True).count()
        parts_count = MachinePart.objects.filter(is_active=True).count()

        parts = MachinePart.objects.filter(is_active=True)

        low_parts = []
        missing_parts = []

        for part in parts:
            qty = part.current_quantity()

            if qty <= 0:
                missing_parts.append(part)
            elif qty < part.min_quantity:
                low_parts.append(part)

        recent_events = (
            MaintenanceEvent.objects
            .select_related("machine")
            .order_by("-date", "-id")[:10]
        )

        return render(request, "maintenance/dashboard.html", locals())