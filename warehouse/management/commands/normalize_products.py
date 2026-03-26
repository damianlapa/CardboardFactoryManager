# warehouse/management/commands/normalize_products.py
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Tuple

from django.core.management.base import BaseCommand
from django.db import transaction


# ---- Normalizacja / heurystyki ----------------------------------------------------------

# Typowe tektury / flute w Twoim systemie
FLUTE_RE = re.compile(r"^(E|B|C|BC|EB|BE|5BC|3B|2W|3W|5W)$", re.I)


def norm_spaces(s: str) -> str:
    return " ".join((s or "").strip().split())


def clean_pipes(name: str) -> str:
    """
    Normalizuje zapis:
    - usuwa wielokrotne spacje
    - normalizuje ' | '
    - usuwa puste segmenty na początku/końcu (np. 'ABC | ' -> 'ABC')
    Nie usuwa pustych segmentów w środku (bo mogą być znaczące), ale w praktyce
    Twoje śmieci to głównie końcówki.
    """
    s = norm_spaces(name)
    if "|" in s:
        parts = [p.strip() for p in s.split("|")]
        # wywal puste na końcu
        while parts and parts[-1] == "":
            parts.pop()
        # wywal puste na początku
        while parts and parts[0] == "":
            parts.pop(0)
        s = " | ".join(parts)
    return s


def looks_like_dimensions(s: str) -> bool:
    """
    Heurystyka:
    - ma cyfry
    - ma przynajmniej jedno 'x'
    - składa się z cyfr + separatorów (x, -, /, ., ,)
    """
    if not s:
        return False
    t = s.strip().lower().replace(" ", "")
    if not any(ch.isdigit() for ch in t):
        return False
    if "x" not in t:
        return False
    return bool(re.fullmatch(r"[0-9x\-/.,]+", t))


def normalize_dimensions(dim: str) -> str:
    # "725x 725 x190" / "725*725*190" -> "725x725x190"
    t = (dim or "").strip().lower().replace(" ", "")
    t = t.replace("*", "x")
    t = re.sub(r"[xX]+", "x", t)
    return t


def normalize_flute(flute: str) -> str:
    return (flute or "").strip().upper()


def build_box_canonical(customer: str, flute: str, dims: str, extra: str = "") -> str:
    parts = [
        clean_pipes(customer).upper(),
        normalize_flute(flute),
        normalize_dimensions(dims),
    ]
    extra = clean_pipes(extra).upper()
    if extra:
        parts.append(extra)
    return " | ".join([p for p in parts if p])


def canonicalize_product_name(name: str) -> str:
    """
    1) Jeśli to 'pudełko' (da się znaleźć flute + dimensions w segmentach po '|'),
       to układamy kanon:
          CUSTOMER | FLUTE | DIMENSIONS | EXTRA
       gdzie EXTRA = reszta segmentów (bez flute i dims) sklejona ' | '.

       Obsługuje m.in.:
         - CUSTOMER | BC | 725x725x190
         - CUSTOMER | 725x725x190 | BC
         - CUSTOMER | BC | 725x... | RAB...
         - CUSTOMER | 3500-220x... | C

    2) Jeśli to nie pudełko (palety, odpady, materiały pomocnicze, dziwne formaty),
       NIE wymyślamy brakujących pól — tylko czyścimy pipe/spacje i robimy UPPER.
    """
    base = clean_pipes(name)

    if "|" not in base:
        return base.upper()

    parts = [p.strip() for p in base.split("|")]
    parts = [p for p in parts if p != ""]

    if len(parts) < 2:
        return base.upper()

    customer = parts[0]
    rest = parts[1:]

    flute_idx = None
    dims_idx = None

    for i, p in enumerate(rest):
        up = p.strip().upper()
        if flute_idx is None and up and FLUTE_RE.fullmatch(up):
            flute_idx = i
        if dims_idx is None and looks_like_dimensions(p):
            dims_idx = i

    if flute_idx is not None and dims_idx is not None:
        flute = rest[flute_idx]
        dims = rest[dims_idx]
        extra_parts = [p for j, p in enumerate(rest) if j not in (flute_idx, dims_idx)]
        extra = " | ".join(extra_parts).strip()
        return build_box_canonical(customer, flute, dims, extra)

    return base.upper()


# ---- Introspekcja FK --------------------------------------------------------------------

def get_fk_related_fields_to_product(ProductModel) -> List[Tuple[type, str]]:
    """
    Zwraca listę (Model, field_name) dla wszystkich relacji FK/O2O wskazujących na Product.
    Dzięki temu nie musisz ręcznie wypisywać zależności.
    """
    related: List[Tuple[type, str]] = []
    for rel in ProductModel._meta.related_objects:
        if not hasattr(rel, "field"):
            continue
        field = rel.field
        if getattr(field, "remote_field", None) and field.remote_field.model == ProductModel:
            model = rel.related_model
            related.append((model, field.name))
    return related


# ---- Komenda ----------------------------------------------------------------------------

@dataclass
class MergePlan:
    canonical: str
    keep_id: int
    drop_ids: List[int]


class Command(BaseCommand):
    help = "Normalizuje Product.name i scala rekordy, które po normalizacji kolidują."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Tylko raport, bez zmian w bazie.")
        parser.add_argument("--apply", action="store_true", help="Wykonaj zmiany (rename/merge).")
        parser.add_argument(
            "--force",
            action="store_true",
            help="Wymuś merge nawet gdy pola (flute/dimensions) różnią się (ostrożnie). "
                 "Po patchu zwykle niepotrzebne.",
        )
        parser.add_argument("--limit", type=int, default=0, help="Przetwórz maks. N grup (0 = bez limitu).")

    def handle(self, *args, **opts):
        from warehouse.models import Product  # local import

        dry = bool(opts["dry_run"])
        apply = bool(opts["apply"])
        force = bool(opts["force"])
        limit = int(opts["limit"] or 0)

        if apply and dry:
            self.stdout.write(self.style.ERROR("Nie używaj jednocześnie --dry-run i --apply."))
            return
        if not apply and not dry:
            self.stdout.write(self.style.WARNING("Podaj --dry-run albo --apply."))
            return

        products = list(Product.objects.all().only("id", "name", "dimensions", "flute", "gsm").order_by("id"))
        self.stdout.write(f"Products total: {len(products)}")

        # FK relacje do przepięcia
        fk_targets = get_fk_related_fields_to_product(Product)
        self.stdout.write(f"FK relations to Product discovered: {len(fk_targets)}")
        for m, f in fk_targets[:10]:
            self.stdout.write(f"  - {m._meta.label}.{f}")
        if len(fk_targets) > 10:
            self.stdout.write("  ...")

        def count_refs(prod_id: int) -> int:
            total = 0
            for model, field_name in fk_targets:
                total += model.objects.filter(**{f"{field_name}_id": prod_id}).count()
            return total

        # Kanon dla każdego produktu
        canonical_by_id: Dict[int, str] = {}
        groups: Dict[str, List[Product]] = defaultdict(list)

        for p in products:
            canonical = canonicalize_product_name(p.name or "")
            canonical_by_id[p.id] = canonical
            groups[canonical].append(p)

        dup_groups = [(canon, ps) for canon, ps in groups.items() if len(ps) > 1]
        rename_only = [(canon, ps[0]) for canon, ps in groups.items() if len(ps) == 1 and ps[0].name != canon]

        self.stdout.write(f"Groups needing MERGE (canonical collisions): {len(dup_groups)}")
        self.stdout.write(f"Products needing RENAME only: {len(rename_only)}")

        def compatible(a: Product, b: Product) -> bool:
            """
            Minimalna zgodność dla merge:
            - jeśli oba mają flute i różne -> konflikt
            - jeśli oba mają dimensions i po normalizacji różne -> konflikt
            UWAGA: po patchu wiele wcześniejszych konfliktów zniknie, bo lepiej parsujemy name.
            """
            if a.flute and b.flute and a.flute.strip().upper() != b.flute.strip().upper():
                return False
            if a.dimensions and b.dimensions and normalize_dimensions(a.dimensions) != normalize_dimensions(b.dimensions):
                return False
            return True

        processed_groups = 0

        # 1) MERGE grup kolizyjnych
        for canonical, ps in sorted(dup_groups, key=lambda x: x[0]):
            if limit and processed_groups >= limit:
                break

            scored = [(count_refs(p.id), p.id, p) for p in ps]
            scored.sort(key=lambda x: (-x[0], x[1]))
            keep = scored[0][2]
            others = [t[2] for t in scored[1:]]

            ok = all(compatible(keep, o) for o in others)
            if not ok and not force:
                self.stdout.write(self.style.WARNING(
                    f"[SKIP] Canonical='{canonical}' ids={[p.id for p in ps]} "
                    f"(różne flute/dimensions). Użyj --force jeśli wiesz co robisz."
                ))
                continue

            self.stdout.write("\n" + "=" * 90)
            self.stdout.write(f"MERGE GROUP canonical: {canonical}")
            self.stdout.write(f"  KEEP:  id={keep.id} name='{keep.name}' refs={count_refs(keep.id)}")
            for o in others:
                self.stdout.write(f"  DROP:  id={o.id} name='{o.name}' refs={count_refs(o.id)}")

            if dry:
                processed_groups += 1
                continue

            with transaction.atomic():
                drop_ids = [o.id for o in others]

                # przepięcie FK
                for model, field_name in fk_targets:
                    model.objects.filter(**{f"{field_name}_id__in": drop_ids}).update(**{f"{field_name}_id": keep.id})

                # rename keep -> canonical
                keep.name = canonical
                keep.save(update_fields=["name"])

                # usuń pozostałe
                for o in others:
                    o.delete()

            processed_groups += 1

        # 2) RENAME singletonów
        renamed = 0
        for canonical, p in sorted(rename_only, key=lambda x: x[1].id):
            if limit and (processed_groups + renamed) >= limit:
                break

            # zabezpieczenie: canonical nie może istnieć jako name innego produktu
            if Product.objects.filter(name=canonical).exclude(id=p.id).exists():
                self.stdout.write(self.style.WARNING(
                    f"[SKIP RENAME] id={p.id} -> '{canonical}' (name już istnieje)."
                ))
                continue

            self.stdout.write(f"RENAME id={p.id}: '{p.name}' -> '{canonical}'")

            if dry:
                renamed += 1
                continue

            with transaction.atomic():
                p.name = canonical
                p.save(update_fields=["name"])
            renamed += 1

        self.stdout.write("\n" + "-" * 90)
        self.stdout.write(self.style.SUCCESS(
            f"DONE. merge_groups_processed={processed_groups}, renamed={renamed}, mode={'DRY' if dry else 'APPLY'}"
        ))
