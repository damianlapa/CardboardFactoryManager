from django.urls import path
from warehousemanager.gluer_views import *
from warehousemanager.customer_views import *
from warehousemanager.absence_views import ProductionEffectiveWorkHoursView
from warehousemanager.employee_views import (EmployeeListView, EmployeeWorkTimeReportView,
                                             EmployeeProductionUnitsAjaxView)
from warehousemanager.views import *


urlpatterns = [
    path('add-gluernumber/', NewGluerNumberAdd.as_view(), name='gluernumber-add'),
]

urlpatterns += [
    path("map-deliveries/", DeliveryPlacesMapView.as_view(), name="delivery_places_map"),
    path("acv/", AllCustomersView.as_view(), name="acv"),
]

urlpatterns += [
    path(
        "statistics/production-effective-hours/",
        ProductionEffectiveWorkHoursView.as_view(),
        name="production_effective_work_hours",
    ),
]

urlpatterns += [
    path("employees/", EmployeeListView.as_view(), name="employee_list"),
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
]

urlpatterns += [
    # ...

    path(
        "profile/pin/",
        PersonPinChangeView.as_view(),
        name="person-pin-change",
    ),
]

# ->>>>>>>>>>>>>>>>>>>>>>>>>>>> MODERN

from warehousemanager.modern_views.absences import (
    ModernAbsenceListView,
    ModernAbsenceCalendarDataView,
    ModernAbsenceDayUpdateView,
)

from warehousemanager.modern_views.vacations import (
    ModernVacationDetailView,
    ModernVacationListView,
)

# ABSENCES

urlpatterns += [
    path(
        "modern/absences/",
        ModernAbsenceListView.as_view(),
        name="modern-absence-list",
    ),

    path(
        "modern/absences/data/",
        ModernAbsenceCalendarDataView.as_view(),
        name="modern-absence-calendar-data",
    ),
    path(
        "modern/absences/day/update/",
        ModernAbsenceDayUpdateView.as_view(),
        name="modern-absence-day-update",
    ),
]

# VACATIONS

urlpatterns += [
    path(
        "modern/vacations/",
        ModernVacationListView.as_view(),
        name="modern-vacation-list",
    ),

    path(
        "modern/vacations/<int:person_id>/",
        ModernVacationDetailView.as_view(),
        name="modern-vacation-detail",
    ),
]

# EMPLOYEES

from warehousemanager.modern_views.employees import (
    ModernEmployeeListView,
)

urlpatterns += [
    path(
        "modern/employees/",
        ModernEmployeeListView.as_view(),
        name="modern-employee-list",
    ),
]