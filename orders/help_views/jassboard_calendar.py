from django.http import JsonResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin

from orders.services.edi.jassboard import JassBoardClient


class JassBoardCalendarView(
    LoginRequiredMixin,
    View,
):
    login_url = "login"

    def get(self, request):
        board_type = (
            request.GET.get("type", "TF35")
            .strip()
            .upper()
        )

        if board_type not in ("TP", "TF2", "TF35"):
            return JsonResponse(
                {
                    "ok": False,
                    "error": "Niepoprawny typ tektury.",
                },
                status=400,
            )

        try:
            client = JassBoardClient()

            calendar = client.get_calendar()

            suffix_map = {
                "TP": "Tp",
                "TF2": "Tf2",
                "TF35": "Tf35",
            }

            suffix = suffix_map[board_type]

            min_key = (
                f"minDataWysylkiDla{suffix}"
            )

            max_key = (
                f"maxDataWysylkiDla{suffix}"
            )

            min_date = calendar.get(
                min_key
            )

            max_date = calendar.get(
                max_key
            )

            if not min_date:
                return JsonResponse(
                    {
                        "ok": False,
                        "error":
                            "JassBoard nie zwrócił minimalnej daty.",
                    },
                    status=502,
                )

            return JsonResponse(
                {
                    "ok": True,
                    "board_type": board_type,
                    "min_date": min_date[:10],
                    "max_date":
                        max_date[:10]
                        if max_date
                        else None,
                }
            )

        except Exception as exc:
            return JsonResponse(
                {
                    "ok": False,
                    "error": str(exc),
                },
                status=500,
            )
