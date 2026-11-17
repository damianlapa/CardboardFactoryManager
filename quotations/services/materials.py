from django.core.paginator import Paginator
from django.db.models import F, Min, Q
from django.db.models.functions import Trim, Upper

from orders.models import CardboardPriceListItem


def material_label(item):
    cardboard = item.cardboard
    price_list = item.price_list

    return (
        f"{cardboard.index} | "
        f"{cardboard.layers}{cardboard.flute} | "
        f"{cardboard.gsm} g/m² | "
        f"{price_list.provider} | "
        f"cennik {price_list.number or price_list.pk}"
    )


def search_materials(params):
    search = params.get("search", "").strip()[:200]
    flute = params.get("flute", "").strip().upper()
    gsm = params.get("gsm", "").strip()

    empty = {
        "rows": [],
        "page": 1,
        "pages": 1,
        "count": 0,
    }

    if flute not in {"", "B", "C", "E", "EB", "BC"}:
        return {
            **empty,
            "error": "Niepoprawna fala.",
        }

    if gsm:
        try:
            gsm = int(gsm)

            if not 1 <= gsm <= 2147483647:
                raise ValueError

        except ValueError:
            return {
                **empty,
                "error": "Podaj poprawną gramaturę.",
            }

    queryset = (
        CardboardPriceListItem.objects
        .select_related(
            "cardboard",
            "price_list__provider",
        )
        .prefetch_related("price_tiers")
    )

    if search:
        queryset = queryset.filter(
            Q(cardboard__index__icontains=search)
            | Q(price_list__provider__name__icontains=search)
            | Q(price_list__number__icontains=search)
        )

    if flute:
        queryset = (
            queryset
            .annotate(
                flute_key=Upper(
                    Trim("cardboard__flute")
                )
            )
            .filter(flute_key=flute)
        )

    if gsm:
        queryset = queryset.filter(
            cardboard__gsm__gte=gsm,
        )

    queryset = (
        queryset
        .annotate(
            lowest_price=Min(
                "price_tiers__price_per_1000_m2"
            )
        )
        .order_by(
            F("lowest_price").asc(nulls_last=True),
            "-price_list__valid_from",
            "pk",
        )
    )

    page = Paginator(queryset, 30).get_page(
        params.get("page")
    )

    rows = []

    for item in page:
        tier = min(
            item.price_tiers.all(),
            key=lambda entry: (
                entry.price_per_1000_m2,
                entry.min_area_m2,
                entry.pk,
            ),
            default=None,
        )

        price_range = ""

        if tier:
            upper = (
                tier.max_area_m2
                if tier.max_area_m2 is not None
                else "∞"
            )

            price_range = (
                f"{tier.min_area_m2}–{upper} m²"
            )

        rows.append({
            "id": item.pk,
            "index": item.cardboard.index,
            "label": material_label(item),
            "gsm": item.cardboard.gsm,
            "flute": item.cardboard.flute,
            "date_start": (
                item.price_list.valid_from.isoformat()
            ),
            "date_end": (
                item.price_list.valid_to.isoformat()
                if item.price_list.valid_to
                else ""
            ),
            "price_per_1000_m2": (
                str(tier.price_per_1000_m2)
                if tier
                else None
            ),
            "price_range": price_range,
        })

    return {
        "rows": rows,
        "page": page.number,
        "pages": page.paginator.num_pages,
        "count": page.paginator.count,
    }