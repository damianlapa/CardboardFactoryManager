import io
import pdfplumber
from decimal import Decimal


def parse_pricelist_pdf(pdf_bytes: bytes):
    """
    Zwraca (provider:str, items:list[dict]).
    items: [{'name': str, 'flute': str, 'weight': int, 'ect': Decimal|None, 'price': int, 'price2': int|None}]
    price/price2 w groszach (int).
    """
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        all_text = ""
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            all_text += page_text + "\n"

    provider = 'TFP' if 'TFP Sp. z o.o.' in all_text else 'JASS'

    lines = (all_text or "").splitlines()
    papers = ['TL3', 'KP2', 'TLW', 'TDWC', 'KLW', 'KLB', 'KLWC', 'RTDC']
    result = []

    if provider == 'TFP':
        for line in lines:
            split_line = line.split()
            for p in papers:
                if p in line and len(split_line) >= 4:
                    name = split_line[0]
                    if not name or len(name) <= 5:
                        continue
                    weight = split_line[1]
                    # ect i price są na końcu linii, czasem sklejone
                    if ',' in split_line[-2]:
                        price_raw = split_line[-1]
                        ect_raw = split_line[-2].replace(',', '.')
                    else:
                        price_raw = ''.join((split_line[-2], split_line[-1]))
                        ect_raw = split_line[-3].replace(',', '.')

                    # wydobycie fali
                    if name[1] == '3':
                        flute = name[3]
                    else:
                        flute = name[2:4]

                    try:
                        ect = Decimal(ect_raw)
                    except Exception:
                        ect = None

                    # price → grosze (int). Tu przyjmuję, że price_raw to np. "123,45" PLN
                    price_raw = price_raw.replace(',', '.')
                    try:
                        price = int(round(float(price_raw) * 100))
                    except Exception:
                        price = 0

                    try:
                        weight_i = int(weight)
                    except Exception:
                        weight_i = 0

                    result.append({
                        'name': name,
                        'flute': flute,
                        'weight': weight_i,
                        'ect': ect,
                        'price': price,
                        'price2': None,
                    })
    else:
        # JASS
        for l in lines:
            if 'FL' in l or 'TB' in l:
                split_line = l.split()
                if len(split_line) < 3:
                    continue
                flute = split_line[0]
                name = split_line[1].replace('*', '')
                ect = None
                price = 0
                price2 = 0
                weight = 0

                # ECT na końcu linii, jeśli jest z przecinkiem
                if ',' in split_line[-1]:
                    try:
                        ect = Decimal(split_line[-1].replace(',', '.'))
                    except Exception:
                        ect = None

                # Szukaj "zł" i bierz poprzedni token jako kwotę
                for idx, el in enumerate(split_line):
                    if el == 'zł' and idx - 1 >= 0:
                        try:
                            val = int(round(float(split_line[idx - 1].replace(',', '.')) * 100))
                        except Exception:
                            val = 0
                        if not price:
                            price = val
                        else:
                            price2 = val

                # Heurystyka wagi wg Twoich reguł
                if ect and price2:
                    weight_token = split_line[-6] if len(split_line) >= 6 else '0'
                elif ect and price:
                    weight_token = split_line[-4] if len(split_line) >= 4 else '0'
                else:
                    weight_token = split_line[-3] if len(split_line) >= 3 else '0'
                try:
                    weight = int(weight_token)
                except Exception:
                    weight = 0

                result.append({
                    'name': name,
                    'flute': flute,
                    'weight': weight,
                    'ect': ect,
                    'price': price2 or price,  # domyślnie główna cena
                    'price2': price if price2 else None,
                })

    return provider, result
