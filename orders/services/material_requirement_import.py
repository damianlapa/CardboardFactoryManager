import ast
import datetime
import re
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from orders.models import (
    ProductMaterialRequirement,
    CardboardGrade,
)
from warehouse.models import Product


ROW_START_RE = re.compile(r"^\s*20\d{2}\s+\|\|")
SPACES_RE = re.compile(r"\s+")

USAGES_RE = re.compile(
    r"(?<!\d)(\d+(?:[.,]\d+)?)\s*"
    r"(?:UŻYTK(?:I|ÓW)?|UZYTK(?:I|OW)?)\b",
    re.IGNORECASE,
)


def clean(value):
    return SPACES_RE.sub(
        " ",
        (value or "").strip(),
    )


def normalize_compare(value):
    value = clean(value).upper()
    value = value.replace("×", "X")

    value = re.sub(
        r"\s*[|]\s*",
        "|",
        value,
    )

    value = re.sub(
        r"\s*[X]\s*",
        "X",
        value,
    )

    return value


def parse_date(value):
    value = clean(value)

    for fmt in (
        "%Y-%m-%d",
        "%Y-%m %d",
        "%Y-%m",
        "%Y",
    ):
        try:
            return datetime.datetime.strptime(
                value,
                fmt,
            ).date()
        except ValueError:
            pass

    return None


def parse_sheet_dimensions(value):
    """
    Oczekiwany format:
        ('1660', '822')
    """

    value = clean(value)

    try:
        parsed = ast.literal_eval(value)
    except (ValueError, SyntaxError):
        return None

    if not isinstance(
        parsed,
        (tuple, list),
    ):
        return None

    if len(parsed) != 2:
        return None

    try:
        first = int(
            str(parsed[0]).strip()
        )

        second = int(
            str(parsed[1]).strip()
        )

    except (
        TypeError,
        ValueError,
    ):
        return None

    if first <= 0 or second <= 0:
        return None

    return first, second


def parse_cardboard(cardboard):
    """
    Rozpoznaje liczbę warstw i falę.

    Przykłady:
        T30B1TWT0473 -> 3, B
        3B422AA       -> 3, B
        T30C1TWT0433 -> 3, C
        3E340AA       -> 3, E
        T5BC1TWT0603 -> 5, BC
        5BC595AA      -> 5, BC
        T5EB1TWT0578 -> 5, EB
        5EB590AA      -> 5, EB
        T50BC...      -> 5, BC
    """

    raw = clean(cardboard).upper()

    raw = (
        raw
        .replace(" ", "")
        .replace("\t", "")
    )

    if not raw:
        return None, ""

    patterns = (
        (
            re.compile(r"^T?30([BCE])"),
            3,
        ),
        (
            re.compile(r"^3([BCE])"),
            3,
        ),
        (
            re.compile(r"^T?5(?:0)?(BC|EB)"),
            5,
        ),
        (
            re.compile(r"^5(?:0)?(BC|EB)"),
            5,
        ),
    )

    for pattern, layers in patterns:
        match = pattern.search(raw)

        if match:
            return layers, match.group(1)

    return None, ""


def normalize_scores(value):
    """
    SCORES jest teraz osobną kolumną.

    Zostawiamy tylko sensowną wartość.
    '-', puste pole i tekstowe uwagi nie są traktowane jako bigi.

    Akceptowane przykłady:
        205/412/205
        128/326
        610
        40/138/56/149/564/162/36/150/40
    """

    value = clean(value)

    if not value:
        return ""

    if value == "-":
        return ""

    # typowy zapis bigów: liczby oddzielone /
    if re.fullmatch(
        r"\d+(?:\s*/\s*\d+)*",
        value,
    ):
        return re.sub(
            r"\s+",
            "",
            value,
        )

    # Innych tekstów typu:
    # KOLOR CZARNY
    # PRZEKŁADKA
    # ZZ0160200
    # nie importujemy jako scores.
    return ""


def extract_pieces_per_sheet(
    scores,
    item,
    name,
):
    """
    Użytki mogą wystąpić w różnych polach historycznych.

    Jeżeli nie ma jawnej informacji, przyjmujemy 1.00.
    """

    text = clean(
        f"{scores} {item} {name}"
    )

    match = USAGES_RE.search(text)

    if not match:
        return Decimal("1.00")

    raw = (
        match.group(1)
        .replace(",", ".")
    )

    try:
        value = Decimal(raw)

    except Exception:
        return Decimal("1.00")

    if value <= 0:
        return Decimal("1.00")

    return value


def build_product_name(
    company,
    flute,
    item,
    name,
):
    """
    Odtwarza sposób tworzenia nazw Product:

        KLIENT | FALA | ITEM | NAZWA

    np.
        PNEUMAT | BC | 400x400x400 |
    """

    company = clean(company).upper()
    flute = clean(flute).upper()
    item = clean(item).lower()
    name = clean(name).upper()

    return (
        f"{company} | "
        f"{flute} | "
        f"{item} | "
        f"{name}"
    )


def record_key(
    company,
    flute,
    item,
    name,
):
    return normalize_compare(
        build_product_name(
            company,
            flute,
            item,
            name,
        )
    )


def resolve_cardboard_grade(cardboard_index):
    """
    Szuka indeksu tektury w pozycjach cenników.

    Zwraca:
        FOUND
        NOT_FOUND
        AMBIGUOUS

    Dla znalezionej tektury:
        min_gsm = gsm - 5%
        min_ect = ect - 5%
        cover = cover z CardboardGrade
    """

    index = clean(cardboard_index).upper()

    if not index:
        return {
            "status": "NOT_FOUND",
            "index": "",
            "grade": None,
            "gsm": None,
            "ect": None,
            "cover": None,
            "candidates": [],
        }

    grades = list(
        CardboardGrade.objects
        .filter(
            index__iexact=index,
            price_list_items__isnull=False,
        )
        .select_related("provider")
        .distinct()
        .order_by(
            "provider__name",
            "id",
        )
    )

    if not grades:
        return {
            "status": "NOT_FOUND",
            "index": index,
            "grade": None,
            "gsm": None,
            "ect": None,
            "cover": None,
            "candidates": [],
        }

    signatures = {
        (
            grade.gsm,
            grade.ect,
            grade.cover,
        )
        for grade in grades
    }

    if len(signatures) != 1:
        return {
            "status": "AMBIGUOUS",
            "index": index,
            "grade": None,
            "gsm": None,
            "ect": None,
            "cover": None,
            "candidates": grades,
        }

    grade = grades[0]

    # ---------------------------------
    # Minimalna gramatura = -5%
    # ---------------------------------

    min_gsm = int(
        Decimal(
            str(grade.gsm)
        )
        * Decimal("0.95")
    )

    # ---------------------------------
    # Minimalne ECT = -5%
    # ---------------------------------

    min_ect = None

    if grade.ect is not None:
        min_ect = (
            Decimal(
                str(grade.ect)
            )
            * Decimal("0.95")
        ).quantize(
            Decimal("0.01")
        )

    return {
        "status": "FOUND",
        "index": index,
        "grade": grade,
        "gsm": min_gsm,
        "ect": min_ect,
        "cover": grade.cover,
        "candidates": grades,
    }


def read_records(path):
    """
    Obsługiwany format:

    YEAR || MONTH || DATE || COMPANY || CARDBOARD ||
    SCORES || ITEM || NAME || QUANTITY || AREA
    """

    path = Path(path)

    text = path.read_text(
        encoding="utf-8-sig",
        errors="replace",
    )

    blocks = []
    current = []

    for raw_line in text.splitlines():

        if ROW_START_RE.match(raw_line):

            if current:
                blocks.append(
                    " ".join(current)
                )

            current = [raw_line]

        elif current:

            current.append(raw_line)

    if current:
        blocks.append(
            " ".join(current)
        )

    results = []

    for block in blocks:

        parts = [
            clean(part)
            for part in block.split(
                " || "
            )
        ]

        # Nowy format ma dokładnie:
        #
        # 0 YEAR
        # 1 MONTH
        # 2 DATE
        # 3 COMPANY
        # 4 CARDBOARD
        # 5 SCORES
        # 6 ITEM
        # 7 NAME
        # 8 QUANTITY
        # 9 AREA

        if len(parts) < 10:
            continue

        year = parts[0]
        month = parts[1]
        date_raw = parts[2]

        company = parts[3]
        cardboard = parts[4]
        scores_raw = parts[5]
        item = parts[6]
        name = parts[7]

        quantity_raw = parts[8]
        dimensions_raw = parts[9]

        date = parse_date(
            date_raw
        )

        dimensions = parse_sheet_dimensions(
            dimensions_raw
        )

        if not date:
            continue

        if not dimensions:
            continue

        try:
            quantity = int(
                quantity_raw
            )
        except (
            TypeError,
            ValueError,
        ):
            quantity = None

        layers, flute = parse_cardboard(
            cardboard
        )

        scores = normalize_scores(
            scores_raw
        )

        pieces_per_sheet = (
            extract_pieces_per_sheet(
                scores_raw,
                item,
                name,
            )
        )

        row = {
            "year": year,
            "month": month,

            "date": date,

            "company": company,

            "cardboard": cardboard,

            "scores_raw": scores_raw,
            "scores": scores,

            "item": item,
            "name": name,

            "quantity": quantity,

            "sheet_length": (
                dimensions[0]
            ),

            "sheet_width": (
                dimensions[1]
            ),

            "layers": layers,

            "flute": flute,

            "pieces_per_sheet":
                pieces_per_sheet,
        }

        results.append(
            row
        )

    return results


def analyze_files(file_paths):
    """
    TYLKO ANALIZA.

    Funkcja nie zapisuje nic do bazy.

    Zasada:
        dla wielu historycznych rekordów tego samego produktu
        wygrywa najnowszy rekord po dacie.

    Wyjątek:
        jeżeli najnowszy rekord nie ma scores,
        szukamy najnowszego wcześniejszego rekordu
        z poprawnymi scores.
    """

    all_records = []
    file_results = []

    for file_path in file_paths:

        records = read_records(
            file_path
        )

        all_records.extend(
            records
        )

        file_results.append(
            {
                "name": Path(
                    file_path
                ).name,

                "records": len(
                    records
                ),
            }
        )

    grouped = defaultdict(list)

    skipped_without_flute = []

    for row in all_records:

        if not row["flute"]:
            skipped_without_flute.append(
                row
            )
            continue

        key = record_key(
            row["company"],
            row["flute"],
            row["item"],
            row["name"],
        )

        grouped[key].append(
            row
        )

    # ---------------------------------
    # Najnowszy rekord produktu wygrywa
    # ---------------------------------

    latest_by_key = {}

    for key, rows in grouped.items():

        rows.sort(
            key=lambda row: (
                row["date"],
            )
        )

        latest = dict(
            rows[-1]
        )

        # scores:
        # najnowszy niepusty zapis z historii

        latest_scores = ""

        for history_row in reversed(rows):
            if history_row["scores"]:
                latest_scores = (
                    history_row["scores"]
                )
                break

        latest["scores"] = (
            latest_scores
        )

        # pieces_per_sheet:
        # funkcja parsera zawsze daje minimum 1,
        # ale zostawiamy mechanizm na przyszłość.

        latest_pieces = None

        for history_row in reversed(rows):

            value = (
                history_row[
                    "pieces_per_sheet"
                ]
            )

            if value is not None:
                latest_pieces = value
                break

        latest[
            "pieces_per_sheet"
        ] = (
            latest_pieces
            if latest_pieces is not None
            else Decimal("1.00")
        )

        # ---------------------------------
        # Indeks tektury -> cenniki
        # ---------------------------------

        cardboard_grade = resolve_cardboard_grade(
            latest["cardboard"]
        )

        latest["cardboard_grade_status"] = (
            cardboard_grade["status"]
        )

        latest["cardboard_grade"] = (
            cardboard_grade["grade"]
        )

        latest["cardboard_grade_candidates"] = (
            cardboard_grade["candidates"]
        )

        latest["min_gsm"] = (
            cardboard_grade["gsm"]
        )

        latest["min_ect"] = (
            cardboard_grade["ect"]
        )

        latest["cover"] = (
            cardboard_grade["cover"]
        )

        latest_by_key[
            key
        ] = latest

    # ---------------------------------
    # Product z bazy
    # ---------------------------------

    products = list(
        Product.objects.all().only(
            "id",
            "name",
        )
    )

    product_map = defaultdict(list)

    for product in products:

        key = normalize_compare(
            product.name
        )

        product_map[key].append(
            product
        )

    matched_items = []
    not_found = []
    ambiguous = []
    already_exists = []
    ready = []
    conflicts = []

    cardboard_grade_found = []
    cardboard_grade_not_found = []
    cardboard_grade_ambiguous = []

    # ---------------------------------
    # Dopasowanie
    # ---------------------------------

    for key, latest in (
        latest_by_key.items()
    ):

        candidates = product_map.get(
            key,
            [],
        )

        if not candidates:

            not_found.append(
                {
                    "key": key,

                    "latest": latest,

                    "expected_name":
                        build_product_name(
                            latest["company"],
                            latest["flute"],
                            latest["item"],
                            latest["name"],
                        ),
                }
            )

            continue

        if len(candidates) > 1:

            ambiguous.append(
                {
                    "key": key,

                    "latest": latest,

                    "candidates":
                        candidates,
                }
            )

            continue

        product = candidates[0]

        history = sorted(
            grouped[key],
            key=lambda row:
                row["date"],
        )

        configurations = {
            (
                row[
                    "sheet_length"
                ],
                row[
                    "sheet_width"
                ],
                row[
                    "cardboard"
                ],
                row[
                    "scores"
                ],
            )
            for row in history
        }

        has_conflict = (
            len(configurations) > 1
        )

        if has_conflict:

            conflicts.append(
                {
                    "product":
                        product,

                    "latest":
                        latest,

                    "history":
                        history,
                }
            )

        existing = (
            ProductMaterialRequirement
            .objects
            .filter(
                product=product
            )
            .first()
        )

        result = {
            "product":
                product,

            "latest":
                latest,

            "existing":
                existing,

            "history_count":
                len(history),

            "has_conflict":
                has_conflict,

            "cardboard_grade_status":
                latest[
                    "cardboard_grade_status"
                ],

            "can_import":
                (
                    latest[
                        "cardboard_grade_status"
                    ]
                    == "FOUND"
                ),
        }

        if (
            latest[
                "cardboard_grade_status"
            ]
            == "FOUND"
        ):
            cardboard_grade_found.append(
                result
            )

        elif (
            latest[
                "cardboard_grade_status"
            ]
            == "AMBIGUOUS"
        ):
            cardboard_grade_ambiguous.append(
                result
            )

        else:
            cardboard_grade_not_found.append(
                result
            )

        matched_items.append(
            result
        )

        if existing:

            already_exists.append(
                result
            )

        else:

            ready.append(
                result
            )

    # ---------------------------------
    # Sortowanie dla widoku
    # ---------------------------------

    ready.sort(
        key=lambda row:
            row["product"].name
    )

    already_exists.sort(
        key=lambda row:
            row["product"].name
    )

    not_found.sort(
        key=lambda row:
            row["expected_name"]
    )

    conflicts.sort(
        key=lambda row:
            row["product"].name
    )

    ambiguous.sort(
        key=lambda row:
            row["key"]
    )

    return {
        "files":
            file_results,

        "total_records":
            len(
                all_records
            ),

        "unique_products":
            len(
                grouped
            ),

        "matched":
            len(
                matched_items
            ),

        "ready_count":
            len(
                ready
            ),

        "importable_count":
            len(
                cardboard_grade_found
            ),

        # dla zgodności z obecnym HTML
        "missing_pieces_count":
            0,

        "already_exists_count":
            len(
                already_exists
            ),

        "not_found_count":
            len(
                not_found
            ),

        "ambiguous_count":
            len(
                ambiguous
            ),

        "conflicts_count":
            len(
                conflicts
            ),

        "cardboard_grade_found_count":
            len(
                cardboard_grade_found
            ),

        "cardboard_grade_not_found_count":
            len(
                cardboard_grade_not_found
            ),

        "cardboard_grade_ambiguous_count":
            len(
                cardboard_grade_ambiguous
            ),

        "cardboard_grade_found":
            cardboard_grade_found,

        "cardboard_grade_not_found":
            cardboard_grade_not_found,

        "cardboard_grade_ambiguous":
            cardboard_grade_ambiguous,

        "skipped_without_flute_count":
            len(
                skipped_without_flute
            ),

        "ready":
            ready,

        "importable":
            cardboard_grade_found,

        "missing_pieces":
            [],

        "matched_items":
            matched_items,

        "already_exists":
            already_exists,

        "not_found":
            not_found,

        "ambiguous":
            ambiguous,

        "conflicts":
            conflicts,

        "skipped_without_flute":
            skipped_without_flute,
    }


from django.db import transaction


@transaction.atomic
def create_requirement_from_analysis_row(row):
    """
    Tworzy ProductMaterialRequirement dla jednego,
    wcześniej przeanalizowanego rekordu.
    """

    product = row["product"]
    latest = row["latest"]

    if ProductMaterialRequirement.objects.filter(
        product=product
    ).exists():
        raise ValueError(
            f"ProductMaterialRequirement już istnieje dla: {product}"
        )

    if latest.get("cardboard_grade_status") != "FOUND":
        raise ValueError(
            "Nie można zapisać: indeks tektury nie został jednoznacznie znaleziony."
        )

    requirement = ProductMaterialRequirement.objects.create(
        product=product,

        sheet_length=latest["sheet_length"],
        sheet_width=latest["sheet_width"],

        pieces_per_sheet=latest.get(
            "pieces_per_sheet",
            Decimal("1.00"),
        ),

        layers=latest.get("layers"),
        flute=latest.get("flute", ""),

        min_gsm=latest.get("min_gsm"),
        min_ect=latest.get("min_ect"),

        cover=latest.get("cover"),

        scores=latest.get(
            "scores",
            "",
        ),

        notes=(
            f"Import historyczny. "
            f"Ostatni rekord: {latest['date']}. "
            f"Indeks tektury: {latest['cardboard']}."
        ),
    )

    return requirement


from django.db import transaction


def get_complete_import_rows(result):
    """
    Zwraca tylko rekordy, które:

    - mają dopasowany Product,
    - nie mają jeszcze ProductMaterialRequirement,
    - mają znaleziony indeks tektury,
    - mają min_gsm,
    - mają min_ect,
    - mają cover,
    - mają wymiary arkusza.

    scores nie jest wymagane.
    pieces_per_sheet ma domyślnie 1.00.
    """

    complete = []

    for row in result.get("ready", []):
        latest = row["latest"]

        if (
            latest.get("cardboard_grade_status") == "FOUND"
            and latest.get("min_gsm") is not None
            and latest.get("min_ect") is not None
            and latest.get("cover")
            and latest.get("sheet_length")
            and latest.get("sheet_width")
        ):
            complete.append(row)

    return complete


@transaction.atomic
def import_complete_rows(result):
    """
    Importuje wszystkie kompletne rekordy.

    Zabezpieczenia:
    - ponownie sprawdza kompletność,
    - pomija rekord, jeżeli ProductMaterialRequirement
      został już wcześniej utworzony.
    """

    complete_rows = get_complete_import_rows(
        result
    )

    created = []
    skipped = []

    for row in complete_rows:

        product = row["product"]
        latest = row["latest"]

        if (
            ProductMaterialRequirement
            .objects
            .filter(product=product)
            .exists()
        ):
            skipped.append(
                {
                    "product": product,
                    "reason": "already_exists",
                }
            )
            continue

        requirement = (
            ProductMaterialRequirement
            .objects
            .create(
                product=product,

                sheet_length=latest[
                    "sheet_length"
                ],

                sheet_width=latest[
                    "sheet_width"
                ],

                pieces_per_sheet=(
                    latest.get(
                        "pieces_per_sheet"
                    )
                    or Decimal("1.00")
                ),

                layers=latest.get(
                    "layers"
                ),

                flute=latest.get(
                    "flute",
                    "",
                ),

                min_gsm=latest.get(
                    "min_gsm"
                ),

                min_ect=latest.get(
                    "min_ect"
                ),

                cover=latest.get(
                    "cover"
                ),

                scores=latest.get(
                    "scores",
                    "",
                ),

                notes=(
                    "Import historyczny. "
                    f"Ostatni rekord: "
                    f"{latest['date']}. "
                    f"Indeks tektury: "
                    f"{latest['cardboard']}."
                ),
            )
        )

        created.append(
            requirement
        )

    return {
        "created_count":
            len(created),

        "skipped_count":
            len(skipped),

        "created":
            created,

        "skipped":
            skipped,
    }