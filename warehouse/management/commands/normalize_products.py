# warehouse/management/commands/normalize_products.py
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Tuple

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Model


def norm_spaces(s: str) -> str:
    return " ".join((s or "").strip().split())


def norm_dimensions(dim: str) -> str:
    # "725x 725 x190" / "725*725*190" -> "725x725x190"
    d = norm_spaces(dim).lower().replace(" ", "")
    d = d.replace("*", "x")
    d = re.sub(r"[xX]+", "x", d)
    return d


@dataclass(frozen=True)
class ProductKey:
    customer: str
    flute: str
    dimensions: str
    extra: str  # opcjonalne


def parse_product_name(name: str) -> ProductKey:
    """
    Wspiera formaty:
      "CUSTOMER | BC | 725x725x190"
      "CUSTOMER | BC | 725x725x190 | EXTRA"
    oraz toleruje różne spacje/pipe.
    """
    raw = norm_spaces(name)
    # rozbij po '|'
    parts = [norm_spaces(p) for p in raw.split("|")]
    parts = [p for p in parts if p != ""]  # usuń puste segmenty
    # minimum 3: customer, flute, dims
    customer = parts[0] if len(parts) > 0 else ""
    flute = parts[1] if len(parts) > 1 else ""
    dims = parts[2] if len(parts) > 2 else ""
    extra = parts[3] if len(parts) > 3 else ""
    return ProductKey(
        customer=norm_spaces(customer).upper(),
        flute=norm_spaces(flute).upper(),
        dimensions=norm_dimensions(dims),
        extra=norm_spaces(extra).upper(),
    )


def build_canonical_name(key: ProductKey) -> str:
    parts = [key.customer, key.flute, key.dimensions]
    if key.extra:
        parts.append(key.extra)
    return " | ".join(parts)


def get_fk_related_fields_to_product(ProductModel) -> List[Tuple[type, str]]:
    """
    Zwraca listę (Model, field_name) dla wszystkich relacji FK/M2O wskazujących na Product.
    Używamy introspekcji Django, żeby nie pomijać przyszłych modeli.
    """
    related = []
    for rel in ProductModel._meta.related_objects:
        # tylko relacje typu FK/M2O (many-to-one) lub O2O z polem w modelu zewnętrznym
        if not hasattr(rel, "field"):
            continue
        field = rel.field
        if getattr(field, "remote_field", None) and field.remote_field.model == ProductModel:
            model = rel.related_model
            related.append((model, field.name))
    return related


class Command(BaseCommand):
    help = "Normalizuje Product.name i scala rekordy, które po normalizacji kolidują."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Tylko raport, bez zmian w bazie.")
        parser.add_argument("--apply", action="store_true", help="Wykonaj zmiany (rename/merge).")
        parser.add_argument("--force", action="store_true", help="Wymuś merge nawet gdy pola różnią się (ostrożnie).")
        parser.add_argument("--limit", type=int, default=0, help="Przetwórz maks. N grup (0 = bez limitu).")

    def handle(self, *args, **opts):
        from warehouse.models import Product  # lokalnie, żeby nie ładować przy imporcie

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

        # 1) Grupowanie po kanonicznej nazwie
        groups: Dict[str, List[Product]] = defaultdict(list)
        parsed: Dict[int, Tuple[ProductKey, str]] = {}

        for p in products:
            key = parse_product_name(p.name or "")
            canonical = build_canonical_name(key)
            parsed[p.id] = (key, canonical)
            groups[canonical].append(p)

        dup_groups = [(canon, ps) for canon, ps in groups.items() if len(ps) > 1]
        rename_only = [(canon, ps[0]) for canon, ps in groups.items() if len(ps) == 1 and ps[0].name != canon]

        self.stdout.write(f"Groups needing MERGE (canonical collisions): {len(dup_groups)}")
        self.stdout.write(f"Products needing RENAME only: {len(rename_only)}")

        # 2) Przygotuj listę relacji FK do przepięcia
        fk_targets = get_fk_related_fields_to_product(Product)
        self.stdout.write(f"FK relations to Product discovered: {len(fk_targets)}")
        if fk_targets:
            for m, f in fk_targets[:10]:
                self.stdout.write(f"  - {m._meta.label}.{f}")
            if len(fk_targets) > 10:
                self.stdout.write("  ...")

        # helper: policz referencje
        def count_refs(prod_id: int) -> int:
            total = 0
            for model, field_name in fk_targets:
                total += model.objects.filter(**{f"{field_name}_id": prod_id}).count()
            return total

        # 3) Raport / wykonanie
        processed_groups = 0

        def compatible(a: Product, b: Product) -> bool:
            # minimalna zgodność pól (w praktyce name->key rozstrzyga)
            # jeśli flute/dimensions są puste, nie blokujemy
            if a.flute and b.flute and a.flute.strip().upper() != b.flute.strip().upper():
                return False
            if a.dimensions and b.dimensions and norm_dimensions(a.dimensions) != norm_dimensions(b.dimensions):
                return False
            return True

        # Najpierw merge kolizji (w tych grupach i tak trzeba coś zrobić)
        for canonical, ps in sorted(dup_groups, key=lambda x: x[0]):
            if limit and processed_groups >= limit:
                break

            # wybór KEEP: najwięcej referencji, potem najniższe id
            scored = [(count_refs(p.id), p.id, p) for p in ps]
            scored.sort(key=lambda x: (-x[0], x[1]))
            keep = scored[0][2]
            others = [t[2] for t in scored[1:]]

            # check zgodności
            ok = all(compatible(keep, o) for o in others)
            if not ok and not force:
                self.stdout.write(self.style.WARNING(
                    f"[SKIP] Canonical='{canonical}' ids={[p.id for p in ps]} (różne flute/dimensions). Użyj --force."
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

            # apply
            with transaction.atomic():
                # przepięcie FK
                for model, field_name in fk_targets:
                    qs = model.objects.filter(**{f"{field_name}_id__in": [o.id for o in others]})
                    qs.update(**{f"{field_name}_id": keep.id})

                # uzupełnij keep.name -> canonical
                keep.name = canonical

                # opcjonalnie uzupełnij pola dimensions/flute z parsowania, jeśli puste
                key, _canon = parsed[keep.id]
                if not keep.flute and key.flute:
                    keep.flute = key.flute
                if not keep.dimensions and key.dimensions:
                    keep.dimensions = key.dimensions

                keep.save(update_fields=["name", "flute", "dimensions"])

                # usuń pozostałe
                for o in others:
                    o.delete()

            processed_groups += 1

        # Potem rename singletonów (bez merge)
        renamed = 0
        for canonical, p in sorted(rename_only, key=lambda x: x[1].id):
            if limit and (processed_groups + renamed) >= limit:
                break

            # bezpieczeństwo: canonical nie może istnieć jako name inny niż ten sam produkt
            from warehouse.models import Product
            if Product.objects.filter(name=canonical).exclude(id=p.id).exists():
                # to powinno już być w dup_groups, ale zostawiamy bezpiecznik
                self.stdout.write(self.style.WARNING(
                    f"[SKIP RENAME] id={p.id} -> '{canonical}' (name już istnieje)."
                ))
                continue

            self.stdout.write(f"RENAME id={p.id}: '{p.name}' -> '{canonical}'")

            if dry:
                renamed += 1
                continue

            with transaction.atomic():
                key, _ = parsed[p.id]
                p.name = canonical
                if not p.flute and key.flute:
                    p.flute = key.flute
                if not p.dimensions and key.dimensions:
                    p.dimensions = key.dimensions
                p.save(update_fields=["name", "flute", "dimensions"])
            renamed += 1

        self.stdout.write("\n" + "-" * 90)
        self.stdout.write(self.style.SUCCESS(
            f"DONE. merge_groups_processed={processed_groups}, renamed={renamed}, mode={'DRY' if dry else 'APPLY'}"
        ))
