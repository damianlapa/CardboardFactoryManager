import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

import pdfplumber

from django.db import transaction

from orders.models import (
    CardboardGrade,
    CardboardPriceList,
    CardboardPriceListItem,
    CardboardPriceTier,
)


# ============================================================
# DATA STRUCTURES
# ============================================================

@dataclass
class ParsedPriceTier:
    min_area_m2: Decimal
    max_area_m2: Decimal | None
    price_per_1000_m2: Decimal


@dataclass
class ParsedCardboard:
    index: str
    layers: int
    flute: str
    gsm: int
    ect: Decimal | None
    composition: str
    cover: str | None
    provider_status: str
    provider_status_raw: str
    tiers: list[ParsedPriceTier]


@dataclass
class ParsedPriceList:
    number: str
    valid_from: object
    valid_to: object | None
    items: list[ParsedCardboard]


# ============================================================
# PUBLIC FUNCTION
# ============================================================

def import_cardboard_price_list(
    file,
    provider,
    user=None,
    dry_run=False,
):
    """
    Importuje PDF z cennikiem tektury.

    file:
        UploadedFile / plik binarny / ścieżka obsługiwana przez pdfplumber

    provider:
        warehouse.Provider

    user:
        użytkownik importujący

    dry_run:
        True -> parsuje i zwraca wynik, ale niczego nie zapisuje

    Zwraca dict ze statystykami.
    """

    parsed = parse_price_list(file)

    result = {
        "format": parsed["format"],
        "number": parsed["price_list"].number,
        "valid_from": parsed["price_list"].valid_from,
        "items": len(parsed["price_list"].items),
        "created_grades": 0,
        "updated_grades": 0,
        "created_items": 0,
        "created_tiers": 0,
        "preview": parsed["price_list"].items,
    }

    if dry_run:
        return result

    with transaction.atomic():

        price_list, _ = CardboardPriceList.objects.update_or_create(
            provider=provider,
            number=parsed["price_list"].number,
            valid_from=parsed["price_list"].valid_from,
            defaults={
                "valid_to": parsed["price_list"].valid_to,
                "created_by": user,
            },
        )

        # ponowny import tego samego PDF nie może dublować pozycji
        price_list.items.all().delete()

        for row in parsed["price_list"].items:

            cardboard, created = CardboardGrade.objects.update_or_create(
                provider=provider,
                index=row.index,
                defaults={
                    "layers": row.layers,
                    "flute": row.flute,
                    "gsm": row.gsm,
                    "ect": row.ect,
                    "composition": row.composition,
                    "cover": row.cover,
                    "is_active": True,
                },
            )

            if created:
                result["created_grades"] += 1
            else:
                result["updated_grades"] += 1

            item = CardboardPriceListItem.objects.create(
                price_list=price_list,
                cardboard=cardboard,
                provider_status=row.provider_status,
                provider_status_raw=row.provider_status_raw,
            )

            result["created_items"] += 1

            for tier in row.tiers:
                CardboardPriceTier.objects.create(
                    item=item,
                    min_area_m2=tier.min_area_m2,
                    max_area_m2=tier.max_area_m2,
                    price_per_1000_m2=tier.price_per_1000_m2,
                )

                result["created_tiers"] += 1

    result["price_list"] = price_list

    return result


# ============================================================
# FORMAT DETECTION
# ============================================================

def parse_price_list(file):

    text = extract_pdf_text(file)

    if "TFP Sp. z o.o." in text:
        return {
            "format": "TFP",
            "price_list": parse_tfp(text),
        }

    if "Oferta Handlowa nr:" in text:
        return {
            "format": "OFFER_1900",
            "price_list": parse_offer_1900(text),
        }

    if "JassBoard Sp. z o.o." in text:
        return {
            "format": "JASS",
            "price_list": parse_jass(text),
        }

    raise ValueError(
        "Nie rozpoznano formatu cennika."
    )


# ============================================================
# PDF
# ============================================================

def extract_pdf_text(file):

    if hasattr(file, "seek"):
        file.seek(0)

    pages = []

    with pdfplumber.open(file) as pdf:

        for page in pdf.pages:

            text = page.extract_text(
                x_tolerance=2,
                y_tolerance=3,
            )

            if text:
                pages.append(text)

    return "\n".join(pages)


# ============================================================
# HELPERS
# ============================================================

def detect_layers_from_index(index):

    match = re.match(
        r"^(\d+)",
        index,
    )

    if not match:
        return 0

    return int(match.group(1))

def detect_jass_cover(value):

    value = (
        value
        .lower()
        .strip()
    )

    if value == "brązowa/brązowa":
        return CardboardGrade.Cover.GREY

    if value in (
        "bielona/brązowa",
        "powlekana/brązowa",
    ):
        return CardboardGrade.Cover.WHITE_ONE_SIDE

    if value in (
        "bielona/bielona",
        "powlekana/bielona",
    ):
        return CardboardGrade.Cover.WHITE_TWO_SIDES

    return CardboardGrade.Cover.OTHER

def decimal_value(value):
    if value is None:
        return None

    value = (
        str(value)
        .strip()
        .replace("\xa0", "")
        .replace(" ", "")
        .replace(",", ".")
    )

    return Decimal(value)


def normalize_composition(value):

    if not value:
        return ""

    value = re.sub(r"\s+", " ", value)

    value = re.sub(
        r"\s*/\s*",
        "/",
        value,
    )

    return value.strip()


def detect_layers_from_flute(flute):

    if flute in ("BC", "EB", "EE", "QC"):
        return 5

    return 3


def detect_cover_from_heading(heading):

    heading = heading.lower()

    if "dwustronnie biał" in heading:
        return CardboardGrade.Cover.WHITE_TWO_SIDES

    if "jednostronnie biał" in heading:
        return CardboardGrade.Cover.WHITE_ONE_SIDE

    if "szar" in heading:
        return CardboardGrade.Cover.GREY

    return None


WHITE_PAPERS = (
    "TLW",
    "KLW",
    "KLWC",
    "TLWC",
    "TDWC",
    "RTDC",
)


def detect_cover_from_composition(composition):

    """
    Drugi format cennika nie podaje pokrycia
    jako osobnej kolumny.

    Określamy je na podstawie zewnętrznych papierów.
    """

    composition = normalize_composition(composition)

    parts = composition.split("/")

    paper_codes = []

    for part in parts:
        match = re.search(
            r"([A-Z0-9]+)",
            part.strip(),
        )

        if match:
            paper_codes.append(match.group(1))

    if not paper_codes:
        return None

    first = paper_codes[0]
    last = paper_codes[-1]

    first_white = first.startswith(WHITE_PAPERS)
    last_white = last.startswith(WHITE_PAPERS)

    if first_white and last_white:
        return CardboardGrade.Cover.WHITE_TWO_SIDES

    if first_white or last_white:
        return CardboardGrade.Cover.WHITE_ONE_SIDE

    return CardboardGrade.Cover.GREY


def normalize_status(value):

    raw = (value or "").upper().strip()

    if raw in ("STD", "STANDARD"):
        return CardboardPriceListItem.ProviderStatus.STANDARD

    if raw in ("NSTD", "NON_STANDARD"):
        return CardboardPriceListItem.ProviderStatus.NON_STANDARD

    if raw in ("SPECIAL", "SPECJALNA"):
        return CardboardPriceListItem.ProviderStatus.SPECIAL

    return CardboardPriceListItem.ProviderStatus.OTHER


# ============================================================
# TFP PARSER
# ============================================================

def parse_tfp(text):

    # ----------------------------------------
    # DATA OBOWIĄZYWANIA
    # ----------------------------------------

    match = re.search(
        r"terminem realizacji od\s+(\d{1,2}\.\d{1,2}\.\d{4})",
        text,
        re.IGNORECASE,
    )

    if not match:
        raise ValueError(
            "TFP: nie znaleziono daty obowiązywania cennika."
        )

    valid_from = datetime.strptime(
        match.group(1),
        "%d.%m.%Y",
    ).date()

    number = f"TFP-{valid_from.isoformat()}"

    items = []

    current_flute = None
    current_cover = None

    # ----------------------------------------
    # LINIE
    # ----------------------------------------

    lines = [
        re.sub(r"\s+", " ", line).strip()
        for line in text.splitlines()
        if line.strip()
    ]

    heading_pattern = re.compile(
        r"Tektury\s+"
        r"(?P<layers>[35])-warstwowe\s+"
        r"(?P<cover>.*?)\s+"
        r"o\s+fal(?:i|ach)\s+"
        r"(?P<flute>[A-Z]+)",
        re.IGNORECASE,
    )

    row_pattern = re.compile(
        r"^"
        r"(?P<index>[A-Z0-9]+)"
        r"\s+"
        r"(?P<gsm>\d+)"
        r"\s+"
        r"(?P<rest>.+?)"
        r"\s+"
        r"(?P<status>STD|NSTD)"
        r"\s+"
        r"(?P<ect>\d+[,.]\d+)"
        r"\s+"
        r"(?P<price>[\d\s]+)"
        r"$"
    )

    current_layers = None

    for line in lines:

        heading = heading_pattern.search(line)

        if heading:

            current_layers = int(
                heading.group("layers")
            )

            current_flute = (
                heading.group("flute")
                .upper()
                .strip()
            )

            current_cover = detect_cover_from_heading(
                heading.group("cover")
            )

            continue

        row = row_pattern.match(line)

        if not row:
            continue

        if not current_flute:
            continue

        index = row.group("index")

        # omijamy przypadkowe nagłówki
        if not index.startswith(("T3", "T30", "T5")):
            continue

        composition = normalize_composition(
            row.group("rest")
        )

        status_raw = row.group("status")

        items.append(
            ParsedCardboard(
                index=index,
                layers=current_layers,
                flute=current_flute,
                gsm=int(row.group("gsm")),
                ect=decimal_value(
                    row.group("ect")
                ),
                composition=composition,
                cover=current_cover,
                provider_status=normalize_status(
                    status_raw
                ),
                provider_status_raw=status_raw,
                tiers=[
                    ParsedPriceTier(
                        min_area_m2=Decimal("0"),
                        max_area_m2=None,
                        price_per_1000_m2=decimal_value(
                            row.group("price")
                        ),
                    )
                ],
            )
        )

    if not items:
        raise ValueError(
            "TFP: nie znaleziono pozycji cennika."
        )

    return ParsedPriceList(
        number=number,
        valid_from=valid_from,
        valid_to=None,
        items=items,
    )


# ============================================================
# SECOND FORMAT - PRICE >=1900 / <1900
# ============================================================

def parse_offer_1900(text):

    # ----------------------------------------
    # NUMBER
    # ----------------------------------------

    number_match = re.search(
        r"Oferta Handlowa nr:\s*([^\s]+)",
        text,
        re.IGNORECASE,
    )

    number = (
        number_match.group(1)
        if number_match
        else "UNKNOWN"
    )

    # ----------------------------------------
    # VALID FROM
    # ----------------------------------------

    date_match = re.search(
        r"Cennik obowiązuje dla zamówień składanych od dnia\s*:\s*"
        r"(\d{4}-\d{2}-\d{2})",
        text,
        re.IGNORECASE,
    )

    if not date_match:
        raise ValueError(
            "Nie znaleziono daty obowiązywania cennika."
        )

    valid_from = datetime.strptime(
        date_match.group(1),
        "%Y-%m-%d",
    ).date()

    # ----------------------------------------
    # LINES
    # ----------------------------------------

    lines = [
        re.sub(r"\s+", " ", line).strip()
        for line in text.splitlines()
        if line.strip()
    ]

    current_flute = None
    current_status = "STANDARD"

    items = []

    flute_pattern = re.compile(
        r"Fala:\s*([A-Z]+)",
        re.IGNORECASE,
    )

    row_pattern = re.compile(
        r"^"
        r"(?P<lp>\d+)"
        r"\s+"
        r"(?P<index>[A-Z0-9]+)"
        r"\s+"
        r"(?P<price_large>\d+)"
        r"\s+"
        r"(?P<price_small>\d+)"
        r"\s+"
        r"(?P<rest>.+)"
        r"\s+"
        r"(?P<gsm>\d+)"
        r"\s+"
        r"(?P<ect>\d+[,.]\d+)"
        r"$"
    )

    for line in lines:

        flute_match = flute_pattern.search(line)

        if flute_match:
            current_flute = (
                flute_match
                .group(1)
                .upper()
                .strip()
            )

            continue

        upper = line.upper()

        if upper == "STANDARD":
            current_status = "STANDARD"
            continue

        if upper in ("SPECJALNA", "SPECIAL"):
            current_status = "SPECIAL"
            continue

        row = row_pattern.match(line)

        if not row:
            continue

        if not current_flute:
            continue

        composition = normalize_composition(
            row.group("rest")
        )

        cover = detect_cover_from_composition(
            composition
        )

        items.append(
            ParsedCardboard(
                index=row.group("index"),
                layers=detect_layers_from_flute(
                    current_flute
                ),
                flute=current_flute,
                gsm=int(row.group("gsm")),
                ect=decimal_value(
                    row.group("ect")
                ),
                composition=composition,
                cover=cover,
                provider_status=normalize_status(
                    current_status
                ),
                provider_status_raw=current_status,
                tiers=[
                    # < 1900
                    ParsedPriceTier(
                        min_area_m2=Decimal("0"),
                        max_area_m2=Decimal("1899.99"),
                        price_per_1000_m2=decimal_value(
                            row.group("price_small")
                        ),
                    ),

                    # >= 1900
                    ParsedPriceTier(
                        min_area_m2=Decimal("1900"),
                        max_area_m2=None,
                        price_per_1000_m2=decimal_value(
                            row.group("price_large")
                        ),
                    ),
                ],
            )
        )

    if not items:
        raise ValueError(
            "Nie znaleziono pozycji w cenniku."
        )

    return ParsedPriceList(
        number=number,
        valid_from=valid_from,
        valid_to=None,
        items=items,
    )


def parse_jass(text):

    # ========================================================
    # DATA OBOWIĄZYWANIA
    # ========================================================

    date_match = re.search(
        r"Oferta obowiązuje dla wysyłek od:\s*(\d{4}-\d{2}-\d{2})",
        text,
        re.IGNORECASE,
    )

    if not date_match:
        raise ValueError(
            "JASS: nie znaleziono daty obowiązywania cennika."
        )

    valid_from = datetime.strptime(
        date_match.group(1),
        "%Y-%m-%d",
    ).date()

    number = f"JASS-{valid_from.isoformat()}"

    # ========================================================
    # LINIE
    # ========================================================

    lines = [
        re.sub(r"\s+", " ", line).strip()
        for line in text.splitlines()
        if line.strip()
    ]

    items = []

    current_status = "STANDARD"

    # fala, symbol, typ, skład, gsm, cena1, cena2, ect
    #
    # przykład:
    # E 3E0293AA* brązowa/brązowa TB090 FL080 TB090 293 0,85 zł 0,87 zł 3,20
    #
    row_pattern_two_prices = re.compile(
        r"^"
        r"(?P<flute>[A-Z]+)"
        r"\s+"
        r"(?P<index>[A-Z0-9*]+)"
        r"\s+"
        r"(?P<cover_type>[^\s]+/[^\s]+)"
        r"\s+"
        r"(?P<composition>.+?)"
        r"\s+"
        r"(?P<gsm>\d+)"
        r"\s+"
        r"(?P<price_large>\d+[,.]\d+)"
        r"\s+zł"
        r"\s+"
        r"(?P<price_small>\d+[,.]\d+)"
        r"\s+zł"
        r"\s+"
        r"(?P<ect>\d+[,.]\d+)"
        r"$"
    )

    # niestandardowe mają czasem tylko jedną cenę
    #
    # przykład:
    # E 3E0386BB* bielona/bielona TW140 FL090 TW120 386 1,25 zł 3,90
    #
    row_pattern_one_price = re.compile(
        r"^"
        r"(?P<flute>[A-Z]+)"
        r"\s+"
        r"(?P<index>[A-Z0-9*]+)"
        r"\s+"
        r"(?P<cover_type>[^\s]+/[^\s]+)"
        r"\s+"
        r"(?P<composition>.+?)"
        r"\s+"
        r"(?P<gsm>\d+)"
        r"\s+"
        r"(?P<price>\d+[,.]\d+)"
        r"\s+zł"
        r"\s+"
        r"(?P<ect>\d+[,.]\d+)"
        r"$"
    )

    for line in lines:

        upper = line.upper()

        # ====================================================
        # STATUS SEKCJI
        # ====================================================

        if "SKŁADY STANDARDOWE" in upper:
            current_status = "STANDARD"
            continue

        if "SKŁADY NIESTANDARDOWE" in upper:
            current_status = "NON_STANDARD"
            continue

        if "NOWOŚĆ" in upper:
            current_status = "SPECIAL"
            continue

        # ====================================================
        # DWIE CENY
        # ====================================================

        match = row_pattern_two_prices.match(line)

        if match:

            flute = match.group("flute").upper().strip()

            raw_index = match.group("index")
            index = raw_index.replace("*", "")

            cover_raw = match.group("cover_type")

            composition = normalize_composition(
                match.group("composition")
            )

            gsm = int(match.group("gsm"))
            ect = decimal_value(match.group("ect"))

            # JASS podaje ceny za 1 m²
            # my zapisujemy PLN / 1000 m²
            price_large = (
                decimal_value(match.group("price_large"))
                * Decimal("1000")
            )

            price_small = (
                decimal_value(match.group("price_small"))
                * Decimal("1000")
            )

            layers = detect_layers_from_index(index)

            cover = detect_jass_cover(
                cover_raw
            )

            items.append(
                ParsedCardboard(
                    index=index,
                    layers=layers,
                    flute=flute,
                    gsm=gsm,
                    ect=ect,
                    composition=composition,
                    cover=cover,
                    provider_status=normalize_status(
                        current_status
                    ),
                    provider_status_raw=current_status,
                    tiers=[
                        ParsedPriceTier(
                            min_area_m2=Decimal("300"),
                            max_area_m2=Decimal("2000"),
                            price_per_1000_m2=price_small,
                        ),
                        ParsedPriceTier(
                            min_area_m2=Decimal("2001"),
                            max_area_m2=None,
                            price_per_1000_m2=price_large,
                        ),
                    ],
                )
            )

            continue

        # ====================================================
        # JEDNA CENA
        # ====================================================

        match = row_pattern_one_price.match(line)

        if match:

            flute = match.group("flute").upper().strip()

            raw_index = match.group("index")
            index = raw_index.replace("*", "")

            cover_raw = match.group("cover_type")

            composition = normalize_composition(
                match.group("composition")
            )

            gsm = int(match.group("gsm"))
            ect = decimal_value(match.group("ect"))

            price = (
                decimal_value(match.group("price"))
                * Decimal("1000")
            )

            layers = detect_layers_from_index(index)

            cover = detect_jass_cover(
                cover_raw
            )

            items.append(
                ParsedCardboard(
                    index=index,
                    layers=layers,
                    flute=flute,
                    gsm=gsm,
                    ect=ect,
                    composition=composition,
                    cover=cover,
                    provider_status=normalize_status(
                        current_status
                    ),
                    provider_status_raw=current_status,
                    tiers=[
                        ParsedPriceTier(
                            min_area_m2=Decimal("0"),
                            max_area_m2=None,
                            price_per_1000_m2=price,
                        ),
                    ],
                )
            )

    if not items:
        raise ValueError(
            "JASS: nie znaleziono pozycji cennika."
        )

    return ParsedPriceList(
        number=number,
        valid_from=valid_from,
        valid_to=None,
        items=items,
    )