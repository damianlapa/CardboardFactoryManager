from decimal import Decimal, ROUND_HALF_UP
from django.db.models import Q
from django.utils import timezone
from orders.models import CardboardPriceList, CardboardPriceListItem


def search_offers(spec):
    area = (Decimal(spec['sheet_length']) * Decimal(spec['sheet_width']) * Decimal(spec['quantity']) / Decimal('1000000'))
    today = timezone.localdate()
    # Only the newest currently valid price list for each provider.
    lists = (CardboardPriceList.objects.filter(valid_from__lte=today)
             .filter(Q(valid_to__isnull=True) | Q(valid_to__gte=today))
             .order_by('provider_id', '-valid_from', '-id'))
    latest = {}
    for price_list in lists:
        latest.setdefault(price_list.provider_id, price_list.pk)
    items = (CardboardPriceListItem.objects.filter(price_list_id__in=latest.values(), cardboard__is_active=True)
             .select_related('cardboard', 'cardboard__provider', 'price_list')
             .prefetch_related('price_tiers'))
    matched, alternatives = [], []
    for item in items:
        grade = item.cardboard
        # Different wave/layer is not a meaningful substitute.
        if grade.layers != spec['layers'] or grade.flute.upper() != spec['flute'].upper():
            continue
        tier = next((t for t in sorted(item.price_tiers.all(), key=lambda x: x.min_area_m2, reverse=True)
                     if t.min_area_m2 <= area and (t.max_area_m2 is None or area <= t.max_area_m2)), None)
        if tier is None:
            continue
        differences = []
        if spec.get('cover') and grade.cover != spec['cover']:
            differences.append('Pokrycie: wymagane %s, oferowane %s' % (dict(grade.Cover.choices).get(spec['cover'], spec['cover']), grade.get_cover_display() if grade.cover else 'brak danych'))
        if spec.get('min_gsm') is not None and grade.gsm < spec['min_gsm']:
            differences.append('Gramatura niższa o %s g/m²' % (spec['min_gsm'] - grade.gsm))
        if spec.get('min_ect') is not None and (grade.ect is None or grade.ect < spec['min_ect']):
            differences.append('ECT: brak danych' if grade.ect is None else 'ECT niższe o %s' % (spec['min_ect'] - grade.ect))
        total = (area * tier.price_per_1000_m2 / Decimal('1000')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        row = dict(grade=grade, item=item, price_list=item.price_list, area=area,
                   price=tier.price_per_1000_m2, total=total,
                   unit_price=(total / spec['quantity']).quantize(Decimal('0.0001')),
                   differences=differences, difference_count=len(differences))
        (alternatives if differences else matched).append(row)
    matched.sort(key=lambda r: (r['total'], r['grade'].provider.name))
    alternatives.sort(key=lambda r: (r['difference_count'], r['total'], r['grade'].provider.name))
    return dict(matched=matched, alternatives=alternatives, area=area)
