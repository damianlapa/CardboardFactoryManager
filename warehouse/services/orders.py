import datetime
import re
from typing import Optional

from warehouse.models import Order, BOM

NUMBER_YEAR_RE = re.compile(r"^(?P<prefix>.*?)(?P<num>\d+)/(?P<yy>\d{2})$")


def next_free_order_id_for_bom(
    bom: BOM,
    date: Optional[datetime.date] = None,
    prefix: Optional[str] = None,
) -> str:
    """
    Zwraca kolejny order_id dla danego BOM, ale pilnuje globalnej unikalności order_id.

    Przykład:
      dla BOM: mamy EUR1/26, EUR2/26, EUR3/26 -> start = EUR4/26
      ale EUR4/26 zajęty (inny BOM) -> zwraca EUR5/26 (lub następny wolny)

    prefix:
      - jeśli podasz: użyje dokładnie tego prefixu (np. "EUR")
      - jeśli nie podasz: spróbuje wykryć prefix z istniejących zamówień tego BOM w danym roku
    """
    d = date or datetime.date.today()
    yy = f"{d.year % 100:02d}"

    # 1) Ustalamy prefix (z parametru lub z istniejących orderów BOM)
    detected_prefix = None
    max_num_for_bom = 0

    qs = Order.objects.filter(bom=bom, order_id__endswith=f"/{yy}").only("order_id")
    for o in qs:
        oid = (o.order_id or "").strip()
        m = NUMBER_YEAR_RE.match(oid)
        if not m or m.group("yy") != yy:
            continue

        p = m.group("prefix")
        n = int(m.group("num"))

        if detected_prefix is None:
            detected_prefix = p
        if n > max_num_for_bom:
            max_num_for_bom = n

    final_prefix = prefix if prefix is not None else detected_prefix
    if final_prefix is None:
        # raise ValueError(
        #     f"Nie da się ustalić prefixu: brak zamówień BOM w formacie <prefix><num>/{yy}. "
        #     f"Podaj prefix jawnie, np. prefix='EUR'."
        # )
        return ""

    # 2) Startujemy od kolejnego numeru dla BOM
    num = max_num_for_bom + 1

    # 3) Globalna unikalność: jeśli zajęte, to increment aż wolne
    while True:
        candidate = f"{final_prefix}{num}/{yy}"
        if not Order.objects.filter(order_id=candidate).exists():
            return candidate
        num += 1
