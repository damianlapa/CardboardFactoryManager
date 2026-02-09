import datetime
import re
from typing import Optional

from warehouse.models import Order, BOM


NUMBER_YEAR_RE = re.compile(r"^(?P<prefix>.*?)(?P<num>\d+)/(?P<yy>\d{2})$")


def next_order_id_for_bom(
    bom: BOM,
    date: Optional[datetime.date] = None,
) -> str:
    """
    Przykłady:
      EUR1/26, EUR3/26, EUR2/26  -> EUR4/26
      ABC-TEST9/25              -> ABC-TEST10/25

    Prefix = dowolny tekst, nieinterpretowany.
    """
    d = date or datetime.date.today()
    yy = f"{d.year % 100:02d}"

    qs = Order.objects.filter(
        bom=bom,
        order_id__endswith=f"/{yy}"
    ).only("order_id")

    max_num = 0
    detected_prefix = None

    for o in qs:
        oid = (o.order_id or "").strip()
        m = NUMBER_YEAR_RE.match(oid)
        if not m:
            continue

        if m.group("yy") != yy:
            continue

        num = int(m.group("num"))
        prefix = m.group("prefix")

        if detected_prefix is None:
            detected_prefix = prefix

        if num > max_num:
            max_num = num

    if detected_prefix is None:
        raise ValueError(
            f"Nie znaleziono żadnego order_id w formacie <prefix><num>/{yy} dla tego BOM"
        )

    return f"{detected_prefix}{max_num + 1}/{yy}"
