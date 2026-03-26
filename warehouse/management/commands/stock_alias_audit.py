import re
from collections import defaultdict

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from warehouse.models import Stock, StockType, Provider, StockAlias


# --- Parsowanie nazw "unikalnych" stocków ---
# Obsługuje m.in.:
# 1) "TFP T30B1TWT0372 [1200x800]"
# 2) "T30B1TWT0372[1200x800]"
# 3) "T30B1TWT0372 [1200x800]"
PATTERNS = [
    re.compile(r"^(?P<prov>\S+)\s+(?P<sku>[^\[]+)\s*\[(?P<dim>[0-9]+\s*x\s*[0-9]+)\]\s*$"),
    re.compile(r"^(?P<sku>[^\[]+)\s*\[(?P<dim>[0-9]+\s*x\s*[0-9]+)\]\s*$"),
    re.compile(r"^(?P<sku>.+?)\s*\[(?P<dim>[0-9]+\s*x\s*[0-9]+)\]\s*$"),
]


def normalize_dim(dim: str) -> str:
    return re.sub(r"\s+", "", dim.lower())


def normalize_sku(sku: str) -> str:
    return sku.strip()


def parse_stock_name(name: str):
    """
    Zwraca dict:
      { 'prov': <str|None>, 'sku': <str>, 'dim': <str> } albo None gdy nie pasuje.
    """
    raw = (name or "").strip()
    for p in PATTERNS:
        m = p.match(raw)
        if not m:
            continue
        d = m.groupdict()
        prov = d.get("prov")
        sku = normalize_sku(d.get("sku") or "")
        dim = normalize_dim(d.get("dim") or "")
        if sku and dim:
            return {"prov": prov, "sku": sku, "dim": dim}
    return None


class Command(BaseCommand):
    help = (
        "Audit stocks that look like provider-coded materials and help create StockAlias mappings.\n"
        "Examples:\n"
        "  python manage.py stock_alias_audit --report\n"
        "  python manage.py stock_alias_audit --suggest --dim 1200x800\n"
        "  python manage.py stock_alias_audit --create-alias --provider TFP --sku T30B1TWT0372 --dim 1200x800 --to-stock-id 123\n"
    )

    def add_arguments(self, parser):
        parser.add_argument("--report", action="store_true", help="Show overview report (groups, candidates).")
        parser.add_argument("--suggest", action="store_true", help="Suggest candidates grouped by dimensions.")
        parser.add_argument("--dim", type=str, default=None, help="Filter by dimensions, e.g. 1200x800")
        parser.add_argument("--provider", type=str, default=None, help="Filter by provider shortcut/name (optional).")
        parser.add_argument("--create-alias", action="store_true", help="Create StockAlias mapping.")
        parser.add_argument("--sku", type=str, default=None, help="SKU/code, e.g. T30B1TWT0372")
        parser.add_argument("--to-stock-id", type=int, default=None, help="Target superstock Stock.id")
        parser.add_argument("--dry-run", action="store_true", help="Do not write changes (for create-alias).")

    def _get_material_type(self):
        try:
            return StockType.objects.get(stock_type="material", unit="PIECE")
        except StockType.DoesNotExist:
            raise CommandError("StockType(material, PIECE) not found.")

    def _find_provider(self, provider_token: str):
        """
        provider_token może być shortcut albo fragment name.
        """
        if not provider_token:
            return None

        qs = Provider.objects.all()
        p = qs.filter(shortcut__iexact=provider_token).first()
        if p:
            return p
        p = qs.filter(name__iexact=provider_token).first()
        if p:
            return p
        p = qs.filter(name__icontains=provider_token).first()
        if p:
            return p

        raise CommandError(f"Provider not found by token: {provider_token}")

    def handle(self, *args, **opts):
        material_type = self._get_material_type()
        dim_filter = normalize_dim(opts["dim"]) if opts.get("dim") else None
        provider_filter_token = opts.get("provider")
        provider_filter_obj = self._find_provider(provider_filter_token) if provider_filter_token else None

        # --- CREATE ALIAS mode ---
        if opts["create_alias"]:
            sku = normalize_sku(opts.get("sku") or "")
            if not sku:
                raise CommandError("--sku is required for --create-alias")
            if not dim_filter:
                raise CommandError("--dim is required for --create-alias (e.g. 1200x800)")
            if not opts.get("to_stock_id"):
                raise CommandError("--to-stock-id is required for --create-alias")

            if not provider_filter_obj:
                raise CommandError("--provider is required for --create-alias (provider shortcut/name)")

            try:
                to_stock = Stock.objects.get(id=opts["to_stock_id"])
            except Stock.DoesNotExist:
                raise CommandError(f"Stock not found: id={opts['to_stock_id']}")

            if to_stock.stock_type_id != material_type.id:
                self.stdout.write(self.style.WARNING(
                    f"WARNING: target stock id={to_stock.id} is not material/PIECE (stock_type={to_stock.stock_type})."
                ))

            exists = StockAlias.objects.filter(
                provider=provider_filter_obj,
                provider_sku=sku,
                dimensions=dim_filter
            ).first()

            if exists:
                self.stdout.write(self.style.SUCCESS(
                    f"Alias already exists: {exists.provider} {exists.provider_sku} [{exists.dimensions}] -> {exists.stock_id}"
                ))
                return

            if opts["dry_run"]:
                self.stdout.write(self.style.WARNING(
                    f"[DRY-RUN] Would create alias: {provider_filter_obj} {sku} [{dim_filter}] -> stock_id={to_stock.id}"
                ))
                return

            with transaction.atomic():
                StockAlias.objects.create(
                    provider=provider_filter_obj,
                    provider_sku=sku,
                    dimensions=dim_filter,
                    stock=to_stock,
                    is_active=True,
                )

            self.stdout.write(self.style.SUCCESS(
                f"Created alias: {provider_filter_obj} {sku} [{dim_filter}] -> stock_id={to_stock.id}"
            ))
            return

        # --- REPORT / SUGGEST mode ---
        stocks = Stock.objects.filter(stock_type=material_type).only("id", "name")
        parsed = []
        for s in stocks.iterator():
            info = parse_stock_name(s.name)
            if not info:
                continue
            if dim_filter and info["dim"] != dim_filter:
                continue
            if provider_filter_obj:
                # tylko te, które mają provider w nazwie i pasuje do shortcut/name
                prov_in_name = (info.get("prov") or "").strip()
                if not prov_in_name:
                    continue
                token = prov_in_name.lower()
                if (provider_filter_obj.shortcut or "").lower() != token and provider_filter_obj.name.lower() != token:
                    # pozwól też na "zawiera"
                    if token not in provider_filter_obj.name.lower():
                        continue
            parsed.append((s, info))

        if not (opts["report"] or opts["suggest"]):
            # domyślnie report
            opts["report"] = True

        # Grupowanie: (prov, sku, dim) i po dim
        by_key = defaultdict(list)
        by_dim = defaultdict(list)

        for s, info in parsed:
            key = (info.get("prov"), info["sku"], info["dim"])
            by_key[key].append(s)
            by_dim[info["dim"]].append((s, info))

        if opts["report"]:
            self.stdout.write("=== STOCK ALIAS AUDIT REPORT ===")
            self.stdout.write(f"Material stocks parsed: {len(parsed)}")
            self.stdout.write(f"Groups (prov, sku, dim): {len(by_key)}")
            self.stdout.write("")

            # Pokaż grupy, gdzie jest potencjalny problem (np. wiele stocków o tym samym kluczu)
            duplicates = [(k, v) for k, v in by_key.items() if len(v) > 1]
            self.stdout.write(f"Duplicate-looking groups: {len(duplicates)}")
            for (prov, sku, dim), stocks_list in duplicates[:50]:
                self.stdout.write(f"- {prov or 'NO_PROV'} :: {sku} [{dim}]  -> stock_ids={[x.id for x in stocks_list]}")
            if len(duplicates) > 50:
                self.stdout.write("... (truncated)")

            self.stdout.write("")
            self.stdout.write("Existing aliases count: %s" % StockAlias.objects.count())
            self.stdout.write("=== END ===")

        if opts["suggest"]:
            self.stdout.write("")
            self.stdout.write("=== SUGGESTIONS GROUPED BY DIMENSIONS ===")
            dims_sorted = sorted(by_dim.keys())
            for dim in dims_sorted[:200]:
                items = by_dim[dim]
                # pokaż top 20 dla wymiaru
                self.stdout.write(f"\nDIM: {dim}  (items={len(items)})")
                for s, info in items[:20]:
                    self.stdout.write(f"  - stock_id={s.id} | name='{s.name}' | prov={info.get('prov')} | sku={info['sku']}")
                if len(items) > 20:
                    self.stdout.write("  ...")
            self.stdout.write("\n=== END ===")
