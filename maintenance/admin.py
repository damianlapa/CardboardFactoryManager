from django.contrib import admin
from .models import (
    Machine,
    PartCategory,
    MachinePart,
    MachinePartAssignment,
    MaintenanceEvent,
    MaintenancePartUsage,
    MaintenanceSupplier,
    MaintenanceSupplierContact,
    MachinePartSupplier
)


@admin.register(Machine)
class MachineAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "manufacturer", "location", "is_active")
    search_fields = ("code", "name", "serial_number", "manufacturer")
    list_filter = ("is_active", "manufacturer")


@admin.register(PartCategory)
class PartCategoryAdmin(admin.ModelAdmin):
    search_fields = ("name",)


class MachinePartSupplierInline(admin.TabularInline):
    model = MachinePartSupplier
    extra = 1
    autocomplete_fields = ["supplier"]


@admin.register(MachinePart)
class MachinePartAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "category", "min_quantity", "recommended_quantity", "is_active")
    search_fields = ("code", "name", "producer")
    list_filter = ("category", "is_active")
    inlines = [MachinePartSupplierInline]


@admin.register(MachinePartAssignment)
class MachinePartAssignmentAdmin(admin.ModelAdmin):
    list_display = ("machine", "part", "quantity_needed", "is_critical")
    search_fields = ("machine__code", "machine__name", "part__code", "part__name")
    list_filter = ("is_critical",)


class MaintenancePartUsageInline(admin.TabularInline):
    model = MaintenancePartUsage
    extra = 1


@admin.register(MaintenanceEvent)
class MaintenanceEventAdmin(admin.ModelAdmin):
    list_display = ("machine", "event_type", "date", "downtime_hours", "created_by")
    list_filter = ("event_type", "date")
    search_fields = ("machine__code", "machine__name", "description")
    inlines = [MaintenancePartUsageInline]


class MaintenanceSupplierContactInline(admin.TabularInline):
    model = MaintenanceSupplierContact
    extra = 1


@admin.register(MaintenanceSupplier)
class MaintenanceSupplierAdmin(admin.ModelAdmin):
    list_display = ("name", "shortcut", "website", "city", "is_active", "main_contact_display")
    search_fields = ("name", "shortcut", "city", "address")
    list_filter = ("is_active", "city")
    inlines = [MaintenanceSupplierContactInline]

    def main_contact_display(self, obj):
        contact = obj.main_contact()
        if not contact:
            return "-"
        return f"{contact.name} | {contact.phone or ''} | {contact.email or ''}"

    main_contact_display.short_description = "Main contact"


@admin.register(MachinePartSupplier)
class MachinePartSupplierAdmin(admin.ModelAdmin):
    list_display = (
        "part",
        "supplier",
        "supplier_code",
        "is_preferred",
        "lead_time_days",
    )
    search_fields = (
        "part__name",
        "part__code",
        "supplier__name",
        "supplier_code",
    )
    list_filter = (
        "is_preferred",
        "supplier",
    )
    autocomplete_fields = ["part", "supplier"]
