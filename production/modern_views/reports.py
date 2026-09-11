import datetime

from django.contrib.auth.mixins import (
    PermissionRequiredMixin,
)
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views import View

from production.models import (
    WorkStation,
)
from production.services.reports import (
    get_production_report,
)
from warehousemanager.models import (
    Person,
)


class ProductionReportsView(
    PermissionRequiredMixin,
    View,
):
    permission_required = (
        "production.view_productionunit"
    )

    login_url = reverse_lazy(
        "login"
    )

    template_name = (
        "production/reports/index.html"
    )

    def get(
        self,
        request,
        *args,
        **kwargs,
    ):
        today = datetime.date.today()

        default_from = (
            today
            - datetime.timedelta(
                days=30
            )
        )


        # ----------------------------------------------------
        # DATE FROM
        # ----------------------------------------------------

        date_from_raw = (
            request.GET.get(
                "date_from"
            )
        )

        try:

            date_from = (
                datetime.date.fromisoformat(
                    date_from_raw
                )
                if date_from_raw
                else default_from
            )

        except ValueError:

            date_from = default_from


        # ----------------------------------------------------
        # DATE TO
        # ----------------------------------------------------

        date_to_raw = (
            request.GET.get(
                "date_to"
            )
        )

        try:

            date_to = (
                datetime.date.fromisoformat(
                    date_to_raw
                )
                if date_to_raw
                else today
            )

        except ValueError:

            date_to = today


        if date_from > date_to:

            date_from, date_to = (
                date_to,
                date_from,
            )


        # ----------------------------------------------------
        # FILTERS
        # ----------------------------------------------------

        station_id = (
            request.GET.get(
                "station"
            )
        )

        worker_id = (
            request.GET.get(
                "worker"
            )
        )


        try:
            station_id = (
                int(station_id)
                if station_id
                else None
            )

        except ValueError:
            station_id = None


        try:
            worker_id = (
                int(worker_id)
                if worker_id
                else None
            )

        except ValueError:
            worker_id = None


        # ----------------------------------------------------
        # REPORT
        # ----------------------------------------------------

        report = (
            get_production_report(
                date_from=date_from,
                date_to=date_to,
                station_id=station_id,
                worker_id=worker_id,
            )
        )


        # ----------------------------------------------------
        # FILTER DATA
        # ----------------------------------------------------

        stations = (
            WorkStation.objects
            .all()
            .order_by(
                "name"
            )
        )


        workers = (
            Person.objects
            .filter(
                occupancy_type="PRODUCTION",
            )
            .order_by(
                "last_name",
                "first_name",
            )
        )


        context = {
            "date_from":
                date_from,

            "date_to":
                date_to,

            "selected_station_id":
                station_id,

            "selected_worker_id":
                worker_id,

            "stations":
                stations,

            "workers":
                workers,

            "report":
                report,

            "summary":
                report["summary"],

            "station_rows":
                report["stations"],

            "unit_rows":
                report["units"],
        }


        return render(
            request,
            self.template_name,
            context,
        )