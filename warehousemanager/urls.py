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


    # Legacy fallback

    path(
        "legacy/employees/",
        EmployeeListView.as_view(),
        name="legacy-employee-list",
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


    # ========================================================
    # PROFILE
    # ========================================================

    path(
        "profile/pin/",
        PersonPinChangeView.as_view(),
        name="person-pin-change",
    ),
]