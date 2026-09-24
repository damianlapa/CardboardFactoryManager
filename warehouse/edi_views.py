from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from warehouse.services.edi.aquila import (
    AquilaOrder,
    AquilaScores,
    build_xml,
    send_order,
)


def get_test_order():
    return AquilaOrder(
        board_grade="3B355A1",
        order_number="TEST-000",

        length=700,
        width=570,

        quantity=755,

        delivery_date="20261016",

        webshop_comment="TEST-005",

        scores=AquilaScores.no_scores(
            width=570,
        ),
    )


@login_required
def edi_test_xml(request):
    try:
        order = get_test_order()

        xml_body = build_xml(order)

        response = HttpResponse(
            xml_body,
            content_type="application/xml; charset=utf-8",
        )

        response["Content-Disposition"] = (
            'attachment; filename="PAKER_TEST.xml"'
        )

        return response

    except ValueError as e:
        return HttpResponse(
            str(e),
            status=400,
        )


@login_required
@csrf_exempt
def edi_test_send(request):
    if request.method != "POST":
        return HttpResponse(
            "Do wysłania wymagany jest POST.",
            status=405,
        )

    try:
        order = get_test_order()

        result = send_order(order)

        return JsonResponse(
            result,
            json_dumps_params={
                "ensure_ascii": False,
                "indent": 2,
            },
        )

    except ValueError as e:
        return JsonResponse(
            {
                "ok": False,
                "error": str(e),
            },
            status=400,
        )

    except Exception as e:
        return JsonResponse(
            {
                "ok": False,
                "error": str(e),
            },
            status=500,
        )