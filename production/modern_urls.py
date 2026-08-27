from django.urls import path

from production.modern_views.dashboard import (
    ProductionMenu,
)
from production.modern_views.orders import (
    AllProductionOrders,
    ChangeProductionStatus,
    OrderDetailsRedirect,
    ProductionOrderCreateView,
    ProductionOrderDetailView,
    ProductionOrderUpdateView,
    UpdateProductionOrderToolView,
    UpdateProductionUnitInline,
    UpdateProductionUnitPersons,
)

from production.modern_views.units import (
    ProductionUnitDeleteView,
    ProductionUnitDetailView,
    ProductionUnitFinishView,
    ProductionUnitMoveDownView,
    ProductionUnitMoveUpView,
    ProductionUnitPlanView,
    ProductionUnitRemoveFromPlanView,
    ProductionUnitStartView,
    ProductionUnitUpdateView,
)

from production.modern_views.workstations import (
    WorkStationDetailView,
    WorkStationListView,
)

from production.modern_views.planning import (
    CurrentWeeklyPlanView,
    WeeklyPlanMoveTaskView,
    WeeklyPlanRemoveTaskView,
    WeeklyPlanView,
)

from production.modern_views.staffing import (
    ProductionStaffingAssignView,
    ProductionStaffingUnassignView,
    ProductionStaffingView,
    ProductionStaffingRequirementsView,
    ProductionStaffingEstimatedTimeView,
)

from production.modern_views.daily_planning import (
    CurrentDailyPlanningView,
    DailyPlanningCreateTaskView,
    DailyPlanningMoveTaskView,
    DailyPlanningRemoveTaskView,
    DailyPlanningView,
)


app_name = "modern_production"


urlpatterns = [

    # ========================================================
    # DASHBOARD
    # ========================================================

    path(
        "",
        ProductionMenu.as_view(),
        name="production-menu",
    ),


    # ========================================================
    # ORDERS
    # ========================================================

    path(
        "orders/",
        AllProductionOrders.as_view(),
        name="all-production-orders",
    ),

    path(
        "orders/add/",
        ProductionOrderCreateView.as_view(),
        name="production-order-add",
    ),

    path(
        "orders/<int:production_order_id>/",
        ProductionOrderDetailView.as_view(),
        name="production-details",
    ),

    path(
        "orders/<int:pk>/edit/",
        ProductionOrderUpdateView.as_view(),
        name="production-order-edit",
    ),

    path(
        "orders/<int:production_order_id>/status/",
        ChangeProductionStatus.as_view(),
        name="production-details-change",
    ),

    path(
        "orders/<int:production_order_id>/tool/",
        UpdateProductionOrderToolView.as_view(),
        name="update_production_order_tool",
    ),

    path(
        "orders/<int:production_order_id>/warehouse/",
        OrderDetailsRedirect.as_view(),
        name="order-redirect",
    ),


    # ========================================================
    # UNIT INLINE ACTIONS
    # ========================================================

    path(
        "units/<int:unit_id>/inline-update/",
        UpdateProductionUnitInline.as_view(),
        name="production-unit-inline-update",
    ),

    path(
        "units/<int:unit_id>/persons-update/",
        UpdateProductionUnitPersons.as_view(),
        name="production-unit-persons-update",
    ),
]

# ============================================================
# UNITS
# ============================================================

urlpatterns += [

    path(
        "units/<int:unit_id>/",
        ProductionUnitDetailView.as_view(),
        name="unit-details",
    ),

    path(
        "units/<int:pk>/edit/",
        ProductionUnitUpdateView.as_view(),
        name="unit-edit",
    ),

    path(
        "units/<int:pk>/delete/",
        ProductionUnitDeleteView.as_view(),
        name="unit-delete",
    ),

    path(
        "units/<int:unit_id>/start/",
        ProductionUnitStartView.as_view(),
        name="unit-start",
    ),

    path(
        "units/<int:unit_id>/finish/",
        ProductionUnitFinishView.as_view(),
        name="unit-finish",
    ),

    path(
        "units/<int:unit_id>/plan/",
        ProductionUnitPlanView.as_view(),
        name="unit-plan",
    ),

    path(
        "units/<int:unit_id>/remove-from-plan/",
        ProductionUnitRemoveFromPlanView.as_view(),
        name="unit-remove-from-plan",
    ),

    path(
        "units/<int:unit_id>/move-up/",
        ProductionUnitMoveUpView.as_view(),
        name="unit-move-up",
    ),

    path(
        "units/<int:unit_id>/move-down/",
        ProductionUnitMoveDownView.as_view(),
        name="unit-move-down",
    ),

]

urlpatterns += [

    path(
        "workstations/",
        WorkStationListView.as_view(),
        name="workstations",
    ),

    path(
        "workstations/<int:workstation_id>/",
        WorkStationDetailView.as_view(),
        name="workstation-details",
    ),

]

# ============================================================
# WEEKLY PLANNING
# ============================================================

urlpatterns += [
    path(
        "planning/",
        CurrentWeeklyPlanView.as_view(),
        name="planning",
    ),

    path(
        "planning/<int:year>/<int:week>/",
        WeeklyPlanView.as_view(),
        name="weekly-plan",
    ),

    path(
        "planning/<int:year>/<int:week>/move/",
        WeeklyPlanMoveTaskView.as_view(),
        name="weekly-plan-move",
    ),

    path(
        "planning/<int:year>/<int:week>/tasks/<int:task_id>/remove/",
        WeeklyPlanRemoveTaskView.as_view(),
        name="weekly-plan-remove",
    ),
    ]

urlpatterns += [
    path(
        "staffing/",
        ProductionStaffingView.as_view(),
        name="staffing",
    ),

    path(
        "staffing/assign/",
        ProductionStaffingAssignView.as_view(),
        name="staffing-assign",
    ),

    path(
        "staffing/unassign/",
        ProductionStaffingUnassignView.as_view(),
        name="staffing-unassign",
    ),

    path(
        "staffing/requirements/",
        ProductionStaffingRequirementsView.as_view(),
        name="staffing-requirements",
    ),

    path(
        "staffing/estimated-time/",
        ProductionStaffingEstimatedTimeView.as_view(),
        name="staffing-estimated-time",
    ),
]

urlpatterns += [
    path(
        "planning/day/",
        CurrentDailyPlanningView.as_view(),
        name="daily-planning-current",
    ),

    path(
        "planning/day/<str:day>/",
        DailyPlanningView.as_view(),
        name="daily-planning",
    ),

    path(
        "planning/day/<str:day>/create/",
        DailyPlanningCreateTaskView.as_view(),
        name="daily-planning-create",
    ),

    path(
        "planning/day/<str:day>/move/",
        DailyPlanningMoveTaskView.as_view(),
        name="daily-planning-move",
    ),

    path(
        "planning/day/<str:day>/tasks/<int:task_id>/remove/",
        DailyPlanningRemoveTaskView.as_view(),
        name="daily-planning-remove",
    ),
]
