# warehouse/management/commands/normalize_product_x_and_merge.py
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Tuple

from django.core.management.base import BaseCommand
from django.db import transaction

# zamienia tylko X pomiędzy cyframi: 1200X800X650 -> 1200x800x650
DIGIT_X_DIGIT = re.compile(r"(?<=\d)[xX](?=\d)")

def norm_spaces(s: str) -> str:
    return " ".join((s or "").strip().split())

def clean_pipes(name: str) -> str:
    s = norm_spaces(name)
    if "|" in s:
        parts = [p.strip() for p in s.split("|")]
        while parts and parts[-1] == "":
            parts.pop()
        while parts and parts[0] == "":
            parts.pop(0)
        s = " | ".join(parts)
    return s

def normalize_x_in_name(name: str) -> str:
    """
    - normalizuje spacje i pipe
    - zamienia 'X'/'x' pomiędzy cyframi na małe 'x'
      (nie rusza liter X w słowach)
    - NIE robi upper/lower dla całego stringa (tylko x w wymiarach)
    """
    s = clean_pipes(name)
    s = DIGIT_X_DIGIT.sub("x", s)
    return s

def get_fk_related_fields_to_product(ProductModel) -> List[Tuple[type, str]]:
    related: List[Tuple[type, str]] = []
    for rel in ProductModel._meta.related_objects:
        if not hasattr(rel, "field"):
            continue
        field = rel.field
        if getattr(field, "remote_field", None) and field.remote_field.model == ProductModel:
            model = rel.related_model
            related.append((model, field.name))
    return related

def count_refs(prod_id: int, fk_targets: List[Tuple[type, str]]) -> int:
    total = 0
    for model, field_name in fk_targets:
        total += model.objects.filter(**{f"{field_name}_id": prod_id}).count()
    return total

@dataclass
class MergeGroup:
    name: str
    keep_id: int
    drop_ids: List[int]


class Command(BaseCommand):
    help = "Normalizuje 'x' w nazwach Product (X między cyframi -> x) i scala duplikaty (unique(name))."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Tylko raport, bez zmian.")
        parser.add_argument("--apply", action="store_true", help="Wykonaj zmiany.")
        parser.add_argument("--limit", type=int, default=0, help="Limit grup/zmian (0=bez limitu).")

    def handle(self, *args, **opts):
        from warehouse.models import Product  # local import

        dry = bool(opts["dry_run"])
        apply = bool(opts["apply"])
        limit = int(opts["limit"] or 0)

        if apply and dry:
            self.stdout.write(self.style.ERROR("Nie używaj jednocześnie --dry-run i --apply."))
            return
        if not apply and not dry:
            self.stdout.write(self.style.WARNING("Podaj --dry-run albo --apply."))
            return

        fk_targets = get_fk_related_fields_to_product(Product)
        self.stdout.write(f"FK relations to Product discovered: {len(fk_targets)}")
        for m, f in fk_targets:
            self.stdout.write(f"  - {m._meta.label}.{f}")

        products = list(Product.objects.all().only("id", "name").order_by("id"))
        self.stdout.write(f"Products total: {len(products)}")

        new_name_by_id: Dict[int, str] = {}
        groups: Dict[str, List[int]] = defaultdict(list)

        for p in products:
            new_name = normalize_x_in_name(p.name or "")
            new_name_by_id[p.id] = new_name
            groups[new_name].append(p.id)

        rename_only = [(pid, new_name_by_id[pid]) for pid in new_name_by_id if new_name_by_id[pid] != next(p.name for p in products if p.id == pid)]
        dup_groups = [(name, ids) for name, ids in groups.items() if len(ids) > 1]

        self.stdout.write(f"Rename candidates: {len(rename_only)}")
        self.stdout.write(f"Duplicate groups after normalization: {len(dup_groups)}")

        processed = 0
        renamed = 0
        merged = 0

        # 1) MERGE duplikatów po normalizacji
        for name, ids in sorted(dup_groups, key=lambda x: x[0]):
            if limit and processed >= limit:
                break
            # wybierz KEEP: najwięcej referencji, potem najniższe ID
            scored = [(count_refs(pid, fk_targets), pid) for pid in ids]
            scored.sort(key=lambda x: (-x[0], x[1]))
            keep_id = scored[0][1]
            drop_ids = [pid for _, pid in scored[1:]]

            self.stdout.write("\n" + "=" * 90)
            self.stdout.write(f"MERGE name: {name}")
            self.stdout.write(f"  KEEP: id={keep_id} refs={count_refs(keep_id, fk_targets)}")
            for d in drop_ids:
                self.stdout.write(f"  DROP: id={d} refs={count_refs(d, fk_targets)}")

            if dry:
                processed += 1
                continue

            with transaction.atomic():
                # przepięcie FK na keep
                for model, field_name in fk_targets:
                    model.objects.filter(**{f"{field_name}_id__in": drop_ids}).update(**{f"{field_name}_id": keep_id})

                # ustaw keep.name = name (już znormalizowane)
                Product.objects.filter(id=keep_id).update(name=name)

                # usuń dropy
                Product.objects.filter(id__in=drop_ids).delete()

            merged += 1
            processed += 1

        # 2) RENAME pozostałych (już bez kolizji)
        # odśwież minimalnie bazę dla uniqueness (po merge)
        if apply:
            existing_names = set(Product.objects.values_list("name", flat=True))
        else:
            existing_names = set(p.name for p in products)

        for pid, new_name in sorted(rename_only, key=lambda x: x[0]):
            if limit and processed >= limit:
                break

            # po merge, mogło zniknąć
            if apply and not Product.objects.filter(id=pid).exists():
                continue

            # jeśli docelowa nazwa już istnieje, to ten przypadek powinien był być w merge;
            # ale na wszelki wypadek skip
            if new_name in existing_names:
                continue

            old_name = Product.objects.get(id=pid).name if apply else next(p.name for p in products if p.id == pid)
            self.stdout.write(f"RENAME id={pid}: '{old_name}' -> '{new_name}'")

            if dry:
                processed += 1
                existing_names.add(new_name)
                continue

            with transaction.atomic():
                Product.objects.filter(id=pid).update(name=new_name)

            renamed += 1
            processed += 1
            existing_names.add(new_name)

        self.stdout.write("\n" + "-" * 90)
        self.stdout.write(self.style.SUCCESS(
            f"DONE. merged={merged}, renamed={renamed}, mode={'DRY' if dry else 'APPLY'}"
        ))
