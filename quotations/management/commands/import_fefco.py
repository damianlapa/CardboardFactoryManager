import io
import re
from pathlib import Path
from urllib.request import Request, urlopen

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from quotations.models import FefcoType


CATALOG_URL = (
    "https://kartony.pl/wp-content/uploads/"
    "2017/05/katalog-fefco-stec.pdf"
)

GROUP_NAMES = {
    "01": "Rolki i arkusze",
    "02": "Opakowania klapowe",
    "03": "Opakowania teleskopowe",
    "04": "Opakowania składane i tace",
    "05": "Konstrukcje wsuwane",
    "06": "Konstrukcje trwale łączone",
    "07": "Konstrukcje klejone jednoczęściowe",
    "09": "Elementy wewnętrzne",
}

CODE_PATTERN = re.compile(
    r"(?<!\d)0[1-79]\d{2}(?!\d)"
)


class Command(BaseCommand):
    help = "Importuje typy FEFCO z katalogu PDF bez nadpisywania danych."

    def add_arguments(self, parser):
        parser.add_argument(
            "--pdf",
            help="Ścieżka do lokalnego PDF zamiast pobierania katalogu.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Pokazuje wynik bez zapisywania zmian.",
        )

    def handle(self, *args, **options):
        try:
            import pdfplumber
        except ImportError as exc:
            raise CommandError(
                "Brak pdfplumber. Zainstaluj: pip install pdfplumber"
            ) from exc

        content = self.load_pdf(options["pdf"])

        try:
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                codes = set()

                for page in pdf.pages:
                    text = page.extract_text() or ""
                    codes.update(CODE_PATTERN.findall(text))

        except Exception as exc:
            raise CommandError(
                f"Nie udało się odczytać katalogu PDF: {exc}"
            ) from exc

        codes = sorted(codes)

        if not codes:
            raise CommandError(
                "W dokumencie nie znaleziono kodów FEFCO. "
                "Nie zapisano żadnych zmian."
            )

        existing = set(
            FefcoType.objects
            .filter(code__in=codes)
            .values_list("code", flat=True)
        )

        missing = [
            code for code in codes
            if code not in existing
        ]

        self.stdout.write(
            f"Znaleziono kodów w PDF: {len(codes)}"
        )
        self.stdout.write(
            f"Już istnieje: {len(existing)}"
        )
        self.stdout.write(
            f"Do dodania: {len(missing)}"
        )

        if options["dry_run"]:
            self.stdout.write(
                "Kody do dodania: "
                + (", ".join(missing) or "brak")
            )
            self.stdout.write(
                self.style.WARNING(
                    "Tryb podglądu — nie zapisano zmian."
                )
            )
            return

        created_count = 0

        with transaction.atomic():
            for code in codes:
                _, created = FefcoType.objects.get_or_create(
                    code=code,
                    defaults={
                        "name": GROUP_NAMES[code[:2]],
                    },
                )
                created_count += int(created)

        self.stdout.write(
            self.style.SUCCESS(
                f"Dodano: {created_count}. "
                f"Pozostawiono istniejących: "
                f"{len(codes) - created_count}."
            )
        )

    def load_pdf(self, local_path):
        try:
            if local_path:
                return Path(local_path).read_bytes()

            self.stdout.write("Pobieranie katalogu FEFCO…")

            request = Request(
                CATALOG_URL,
                headers={"User-Agent": "Mozilla/5.0"},
            )

            with urlopen(request, timeout=30) as response:
                return response.read()

        except OSError as exc:
            raise CommandError(
                f"Nie udało się wczytać PDF: {exc}"
            ) from exc