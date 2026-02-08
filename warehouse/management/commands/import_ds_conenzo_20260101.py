import datetime
import re
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from warehouse.models import DeliverySpecial, DeliverySpecialItem


DATA = """
108     0.01    CONENZO | B | 655x390 | KSM106, KSM206
28      0.01    CONENZO | B | 400x275x215 | CSM101, CSP101
54      0.01    CONENZO | B | 305x290x125 | BSM201, BSP201
56      0.01    CONENZO | B | 696x401 | KSM108, KSP108
697     0.01    CONENZO | B | 325x315 | ASM101, ASP101
37      0.01    CONENZO | B | 658x393x171 | KSM106, KSM206
78      0.01    CONENZO | B | 285x175x90 | GSM018
151     0.01    CONENZO | B | 325x180x119 | DSM101
85      0.01    CONENZO | B | 320x220x130 | ASM201, ASP201
53      0.01    CONENZO | B | 385x345 | BSM101, BSM202
36      0.01    CONENZO | B | 300x285 | BSM201, BSP201
304     0.01    CONENZO | B | 395x270 | CSM101, CSP101
72      0.01    CONENZO | B | 250x155 | DSM102, DSP102
304     0.01    CONENZO | B | 328x318x127 | ASM101, ASP101
11      0.01    CONENZO | B | 388x348x115 | BSM101, BSM202
103     0.01    CONENZO | B | 253x158x100 | DSM102, DSP102
27      0.01    CONENZO | B | 303x288x120 | BSM201, BSP201
217     0,01    CONENZO | B | 318x218x125 | ASM201, ASP201
41      0.01    CONENZO | B | 174x110 | GSM002, GSM004
37      0.01    CONENZO | E | 601x330 | BSM401
121     0.01    CONENZO | E | 594x401 | DSM, DSB, DSC, DSP
6       0.01    CONENZO | E | 587x397 | DSM, DSB, DSC, DSP
47      0.01    CONENZO | E | 502x309 | BSM004, BSM074
6       0.01    CONENZO | B | 701x406x270 | KSM108, KSP108 // ilość, cena, nazwa
""".strip()


def _parse_decimal(s: str) -> Decimal:
    return Decimal(s.replace(",", ".").strip())


def _clean_name(name: str) -> str:
    # ustandaryzuj whitespace
    name = " ".join(name.strip().split())
    # ustandaryzuj pipe spacing
    if "|" in name:
        parts = [p.strip() for p in name.split("|")]
        while parts and parts[-1] == "":
            parts.pop()
        name = " | ".join(parts)
    # max_length=64 w DeliverySpecialItem.name
    if len(name) > 64:
        name = name[:64].rstrip()
    return name


class Command(BaseCommand):
    help = "Tworzy DeliverySpecial (2026-01-01) i importuje itemy z hardcoded DATA."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Nie zapisuje zmian, tylko wypisuje co zrobi.",
        )
        parser.add_argument(
            "--ds-name",
            default="GOTOWE IMPORT 2026-01-01 (CONENZO)",
            help="Nazwa DeliverySpecial (musi być unikalna).",
        )
        parser.add_argument(
            "--provider",
            default="IMPORT",
            help="DeliverySpecial.provider (tekst).",
        )

    @transaction.atomic
    def handle(self, *args, **opts):
        dry = opts["dry_run"]
        ds_name = (opts["ds_name"] or "").strip()
        provider = (opts["provider"] or "").strip() or "IMPORT"
        ds_date = datetime.date(2026, 1, 1)

        if not ds_name:
            raise CommandError("--ds-name nie może być pusty")

        # utwórz delivery special
        ds, created = DeliverySpecial.objects.get_or_create(
            name=ds_name,
            defaults={
                "provider": provider,
                "date": ds_date,
                "description": "Import z hardcoded DATA (CONENZO)",
                "processed": False,
            },
        )
        if ds.date != ds_date:
            raise CommandError(
                f"DeliverySpecial '{ds.name}' już istnieje, ale ma datę {ds.date} (oczekiwano {ds_date})."
            )

        self.stdout.write(self.style.SUCCESS(
            f"DeliverySpecial: name='{ds.name}' date={ds.date} created={created}"
        ))

        created_count = 0
        updated_count = 0
        skipped_count = 0

        # parse lines
        for lineno, raw in enumerate(DATA.splitlines(), start=1):
            line = raw.strip()
            if not line:
                continue

            # usuń komentarz // ...
            line = re.split(r"\s//", line, maxsplit=1)[0].strip()
            if not line:
                continue

            # split po whitespace: qty, price, reszta to name
            parts = line.split()
            if len(parts) < 3:
                raise CommandError(
                    f"Linia {lineno}: zły format. Oczekuję: qty price name. Dostałem: {raw!r}"
                )

            qty_s = parts[0]
            price_s = parts[1]
            name_s = " ".join(parts[2:])

            try:
                qty = int(qty_s)
            except Exception:
                raise CommandError(f"Linia {lineno}: niepoprawna ilość: {qty_s!r}")

            try:
                price = _parse_decimal(price_s)
            except Exception:
                raise CommandError(f"Linia {lineno}: niepoprawna cena: {price_s!r}")

            if qty <= 0:
                skipped_count += 1
                continue

            name = _clean_name(name_s)
            if not name:
                raise CommandError(f"Linia {lineno}: pusta nazwa.")

            if dry:
                self.stdout.write(f"[DRY] line={lineno} qty={qty} price={price} name='{name}'")
                continue

            obj, it_created = DeliverySpecialItem.objects.get_or_create(
                delivery=ds,
                name=name,
                defaults={
                    "quantity": qty,
                    "price": price,
                    "processed": False,
                },
            )

            if it_created:
                created_count += 1
            else:
                obj.quantity = qty
                obj.price = price
                obj.processed = False
                obj.save(update_fields=["quantity", "price", "processed"])
                updated_count += 1

        if dry:
            raise CommandError("DRY-RUN zakończony — transakcja przerwana celowo (nic nie zapisano).")

        self.stdout.write(self.style.SUCCESS(
            f"OK. Items: created={created_count}, updated={updated_count}, skipped={skipped_count}"
        ))
