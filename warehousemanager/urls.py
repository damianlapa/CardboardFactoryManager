from django.urls import path
from warehousemanager.gluer_views import *
from warehousemanager.customer_views import *
from warehousemanager.absence_views import ProductionEffectiveWorkHoursView
from warehousemanager.employee_views import (EmployeeListView, EmployeeWorkTimeReportView,
                                             EmployeeProductionUnitsAjaxView)


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