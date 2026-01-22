from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count

from warehouse.models import (
    Stock,
    WarehouseStock,
    WarehouseStockHistory,
    ProductSell3,
    BOMPart,
)


def _normalize_name(name: str) -> str:
    """
    Pancerny normalizer:
    - strip() całości
    - collapse whitespace (podwójne spacje -> jedna)
    - jeśli jest '|': strip segmentów, usuń puste segmenty na końcu
      i składaj jako ' | '
    """
    if name is None:
        return ""

    raw = " ".join(name.strip().split())  # collapse whitespace + strip
    if "|" not in raw:
        return raw

    parts = [p.strip() for p in raw.split("|")]

    # USUŃ puste segmenty na końcu, żeby nie produkować " | " na końcu
    while parts and parts[-1] == "":
        parts.pop()

    return " | ".join(parts)



class Command(BaseCommand):
    help = "Normalize Stock.name (trim/format) and merge conflicts by (name, stock_type)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would change, without modifying the database.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Limit number of Stock rows to process (for testing).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        limit = options["limit"]

        qs = Stock.objects.all().order_by("id")
        if limit:
            qs = qs[:limit]

        changed = 0
        merged = 0

        for s in qs:
            old = s.name or ""
            new = _normalize_name(old)

            if new == old:
                continue

            # czy istnieje już stock docelowy o tej samej nazwie i stock_type?
            target = (
                Stock.objects
                .filter(name=new, stock_type_id=s.stock_type_id)
                .exclude(id=s.id)
                .order_by("id")
                .first()
            )

            if dry_run:
                if target:
                    self.stdout.write(
                        f"MERGE Stock id={s.id} -> id={target.id} | '{old}' -> '{new}'"
                    )
                else:
                    self.stdout.write(
                        f"RENAME Stock id={s.id} | '{old}' -> '{new}'"
                    )
                changed += 1
                continue

            if target:
                # ---- MERGE s -> target ----
                # 1) BOMPart
                BOMPart.objects.filter(part=s).update(part=target)

                # 2) WarehouseStock: mogą powstać duplikaty (warehouse, stock)
                #    więc merge per warehouse
                ws_list = list(WarehouseStock.objects.filter(stock=s).select_related("warehouse"))
                for ws in ws_list:
                    # znajdź wszystkie WS dla (warehouse, target_stock)
                    targets = (
                        WarehouseStock.objects
                        .filter(warehouse=ws.warehouse, stock=target)
                        .order_by("id")
                    )

                    target_ws = targets.first()
                    if not target_ws:
                        # nie ma żadnego -> bierzemy bieżący ws jako docelowy, ale podmieniamy stock
                        ws.stock = target
                        ws.save(update_fields=["stock"])
                        target_ws = ws
                    else:
                        # jeśli jest wiele -> scalamy je do pierwszego
                        extra_targets = targets.exclude(id=target_ws.id)
                        if extra_targets.exists():
                            for dup in extra_targets:
                                target_ws.quantity += dup.quantity
                                target_ws.save(update_fields=["quantity"])

                                WarehouseStockHistory.objects.filter(warehouse_stock=dup).update(
                                    warehouse_stock=target_ws)
                                ProductSell3.objects.filter(warehouse_stock=dup).update(warehouse_stock=target_ws)

                                dup.delete()

                        # teraz scalamy bieżący ws (stary stock) do target_ws
                        if ws.id != target_ws.id:
                            target_ws.quantity += ws.quantity
                            target_ws.save(update_fields=["quantity"])

                            WarehouseStockHistory.objects.filter(warehouse_stock=ws).update(warehouse_stock=target_ws)
                            ProductSell3.objects.filter(warehouse_stock=ws).update(warehouse_stock=target_ws)

                            ws.delete()

                # 3) usuń stary Stock
                s.delete()
                merged += 1
                changed += 1
            else:
                # ---- RENAME ----
                s.name = new
                s.save(update_fields=["name"])
                changed += 1

        self.stdout.write(self.style.SUCCESS(f"Done. changed={changed}, merged={merged}"))

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN: no changes were made."))
