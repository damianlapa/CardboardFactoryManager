from django.urls import path

from warehousemanager.gluer_views import *
from warehousemanager.customer_views import *
from warehousemanager.absence_views import (
    ProductionEffectiveWorkHoursView,
)
from warehousemanager.employee_views import (
    EmployeeListView,
    EmployeeWorkTimeReportView,
    EmployeeProductionUnitsAjaxView,
)
from warehousemanager.views import *

from warehousemanager.modern_views.absences import (
    ModernAbsenceListView,
    ModernAbsenceCalendarDataView,
    ModernAbsenceDayUpdateView,
)
from warehousemanager.modern_views.vacations import (
    ModernVacationDetailView,
    ModernVacationListView,
)
from warehousemanager.modern_views.employees import (
    ModernEmployeeListView,
    ModernEmployeeDetailView,
)
from warehousemanager.modern_views.punches import (
    ModernPunchCreateView,
    ModernPunchDeleteView,
    ModernPunchDetailView,
    ModernPunchListView,
    ModernPunchUpdateView,
)

from warehousemanager.modern_views.colors import (
    ModernBucketDetailView,
    ModernColorDetailView,
    ModernColorListView,
)

from warehousemanager.modern_views.polymers import (
    PolymerCreateView,
    PolymerDeleteView,
    PolymerDetailView,
    PolymerListView,
    PolymerUpdateView,
    PolymerServiceCreateView,
    PolymerServiceDeleteView,
    PolymerServiceUpdateView
)


urlpatterns = [

    # ========================================================
    # GLUER NUMBERS
    # ========================================================

    path(
        "add-gluernumber/",
        NewGluerNumberAdd.as_view(),
        name="gluernumber-add",
    ),


    # ========================================================
    # CUSTOMERS / MAP
    # ========================================================

    path(
        "map-deliveries/",
        DeliveryPlacesMapView.as_view(),
        name="delivery_places_map",
    ),

    path(
        "acv/",
        AllCustomersView.as_view(),
        name="acv",
    ),


    # ========================================================
    # STATISTICS
    # ========================================================

    path(
        "statistics/production-effective-hours/",
        ProductionEffectiveWorkHoursView.as_view(),
        name="production_effective_work_hours",
    ),


    # ========================================================
    # EMPLOYEES
    # ACTIVE: MODERN
    # ========================================================

    path(
        "employees/",
        ModernEmployeeListView.as_view(),
        name="employee_list",
    ),

    path(
        "person/<int:person_id>/",
        ModernEmployeeDetailView.as_view(),
        name="person-details",
    ),


    # Legacy fallback

    path(
        "legacy/employees/",
        EmployeeListView.as_view(),
        name="legacy-employee-list",
    ),

    path(
        "legacy/person/<int:person_id>/",
        PersonDetailView.as_view(),
        name="legacy-person-details",
    ),


    # Work time report - still legacy

    path(
        "employees/work-time-report/",
        EmployeeWorkTimeReportView.as_view(),
        name="employee_work_time_report",
    ),

    path(
        "employees/work-time-report/person/<int:person_id>/units/",
        EmployeeProductionUnitsAjaxView.as_view(),
        name="employee_production_units_ajax",
    ),


    # ========================================================
    # ABSENCES
    # ACTIVE: MODERN
    # ========================================================

    path(
        "absences-list/",
        ModernAbsenceListView.as_view(),
        name="absence-list",
    ),

    path(
        "absences-list/data/",
        ModernAbsenceCalendarDataView.as_view(),
        name="absence-calendar-data",
    ),

    path(
        "absences-list/day/update/",
        ModernAbsenceDayUpdateView.as_view(),
        name="absence-day-update",
    ),


    # Legacy fallback

    path(
        "legacy/absences-list/",
        AbsencesList.as_view(),
        name="legacy-absence-list",
    ),

    path(
        "legacy/absences-list/data/",
        AbsencesAndHolidays.as_view(),
        name="legacy-absence-calendar-data",
    ),

    # ============================================================
    # VACATIONS
    # ACTIVE: MODERN
    # ============================================================

    path(
        "vacations/",
        ModernVacationListView.as_view(),
        name="vacations",
    ),

    path(
        "vacations/<int:person_id>/",
        ModernVacationDetailView.as_view(),
        name="vacation-person",
    ),

    # Legacy fallback

    path(
        "legacy/vacations/",
        AvailableVacation.as_view(),
        name="legacy-vacations",
    ),

    path(
        "legacy/vacations/<int:person_id>/",
        PersonsVacations.as_view(),
        name="legacy-vacation-person",
    ),

    # ============================================================
    # PUNCHES - MODERN
    # ============================================================

    path(
        "punches/",
        ModernPunchListView.as_view(),
        name="punches",
    ),

    path(
        "punches/add/",
        ModernPunchCreateView.as_view(),
        name="punch-add",
    ),

    path(
        "punch/<int:punch_id>/",
        ModernPunchDetailView.as_view(),
        name="punch-details",
    ),

    path(
        "punch/<int:punch_id>/edit/",
        ModernPunchUpdateView.as_view(),
        name="punch-edit",
    ),

    path(
        "punch/<int:punch_id>/delete/",
        ModernPunchDeleteView.as_view(),
        name="punch-delete",
    ),

    # ============================================================
    # PUNCHES - LEGACY FALLBACK
    # ============================================================

    path(
        "legacy/punches/",
        PunchesList.as_view(),
        name="legacy-punches",
    ),

    path(
        "legacy/punches/add/",
        PunchAdd.as_view(),
        name="legacy-punch-add",
    ),

    path(
        "legacy/punch/<int:punch_id>/",
        PunchDetails.as_view(),
        name="legacy-punch-details",
    ),

    path(
        "legacy/punch/<int:punch_id>/edit/",
        PunchEdit.as_view(),
        name="legacy-punch-edit",
    ),

    path(
        "legacy/punch/<int:punch_id>/delete/",
        PunchDelete.as_view(),
        name="legacy-punch-delete",
    ),

    # COLORS - MODERN

    path(
        "colors/",
        ModernColorListView.as_view(),
        name="colors",
    ),

    path(
        "colors/<int:color_id>/",
        ModernColorDetailView.as_view(),
        name="color-details",
    ),

    path(
        "colors/bucket/<int:bucket_id>/",
        ModernBucketDetailView.as_view(),
        name="bucket-details",
    ),

    # COLORS - LEGACY

    path(
        "legacy/colors/",
        ColorListView.as_view(),
        name="legacy-colors",
    ),

    path(
        "legacy/colors/<int:color_id>/",
        ColorDetail.as_view(),
        name="legacy-color-details",
    ),

    path(
        "legacy/colors/bucket/<int:bucket_id>/",
        BucketDetail.as_view(),
        name="legacy-bucket-details",
    ),

    # ========================================================
    # POLYMERS
    # ========================================================

    path(
        "polymers/",
        PolymerListView.as_view(),
        name="polymers",
    ),

    path(
        "polymers/<int:polymer_id>/",
        PolymerDetailView.as_view(),
        name="polymer-details",
    ),

    path(
        "polymers/create/",
        PolymerCreateView.as_view(),
        name="polymer-create",
    ),

    path(
        "polymers/<int:pk>/update/",
        PolymerUpdateView.as_view(),
        name="polymer-update",
    ),

    path(
        "polymers/<int:pk>/delete/",
        PolymerDeleteView.as_view(),
        name="polymer-delete",
    ),

    path(
        "photopolymers/service/create/",
        PolymerServiceCreateView.as_view(),
        name="polymer-service-create",
    ),

    path(
        "photopolymers/service/<int:pk>/update/",
        PolymerServiceUpdateView.as_view(),
        name="polymer-service-update",
    ),

    path(
        "photopolymers/service/<int:pk>/delete/",
        PolymerServiceDeleteView.as_view(),
        name="polymer-service-delete",
    ),

    # ========================================================
    # PROFILE
    # ========================================================


    path(
        "profile/pin/",
        PersonPinChangeView.as_view(),
        name="person-pin-change",
    ),
]