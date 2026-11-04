"""Clearly labelled market assessments; never substitutes for an executable quote."""
from datetime import datetime
from decimal import Decimal
from hashlib import sha256
from functools import lru_cache
from pathlib import Path
import re

from pilog_cfr_dss.sources.urea_reports import _text
from pilog_cfr_dss.calculations.freight_pricing import comparison_delta

COUNTRIES = {
    'Vietnam': ('CFR Vietnam (granular)', 'FBIFA04'),
    'Thailand': ('CFR Thailand (granular)', 'FBVTO04'),
    'Philippines': ('CFR Philippines (granular)', 'FBPTO04'),
    'Brazil': ('CFR Brazil urea (granular)', 'FGUBC04'),
}

# Destination mapping follows the named assessment: it is not an assertion
# that an assessment is specific to every terminal in the country.
ARGUS_CFR = {
    'Australia': 'Australia (cfr)', 'Brazil': 'Brazil (cfr)',
    'Argentina': 'Argentina (cfr)', 'India': 'India (cfr)',
    'Romania': 'Romania (cfr)', 'United States': 'US Gulf (cfr)',
    'Mexico': 'Mexico (cfr) west coast',
    'Indonesia': 'Southeast Asia (cfr)', 'Malaysia': 'Southeast Asia (cfr)',
    'Singapore': 'Southeast Asia (cfr)', 'Brunei': 'Southeast Asia (cfr)',
    'Vietnam': 'Southeast Asia (cfr)', 'Thailand': 'Southeast Asia (cfr)',
    'Philippines': 'Southeast Asia (cfr)',
}
ARGUS_PORT_CFR = {
    'Varna': 'Romania (cfr)', 'Batumi': 'Romania (cfr)',
    'Trabzon': 'Romania (cfr)', 'Yuzhnyy': 'Romania (cfr)',
    'Novorossiysk': 'Romania (cfr)',
}


def read_argus_comparables(root: Path) -> dict:
    """Read only the granular urea section and preserve FOB/CFR basis."""
    candidates = []
    for path in (root / 'public').glob('Argus*Nitrogen*.pdf'):
        header = _text(path, 0)
        match = re.search(r'Issue\s+\S+\s*\|\s*\w+\s+(\d{1,2}\s+\w+\s+\d{4})', header)
        if match:
            candidates.append((datetime.strptime(match.group(1), '%d %B %Y'), path))
    if not candidates:
        raise ValueError('Laporan Argus dengan tanggal terbaca belum tersedia')
    date = max(item[0] for item in candidates)
    files = [p for d, p in candidates if d == date]
    if len({sha256(p.read_bytes()).hexdigest() for p in files}) != 1:
        raise ValueError('Ada beberapa laporan Argus berbeda pada tanggal yang sama')
    path = files[0]
    text = _text(path, 1)
    section = text.split('Granular urea - fob bulk', 1)
    if len(section) != 2:
        raise ValueError('Tabel urea granular Argus tidak dikenali')
    section = section[1].split('Sustainable Nitrogen prices', 1)[0]
    digest = sha256(path.read_bytes()).hexdigest()

    def find(label, basis):
        match = re.search(r'(?m)^' + re.escape(label) + r'\s+(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s', section)
        if not match:
            return None
        low, high = match.groups()
        if Decimal(low) <= 0 or Decimal(high) < Decimal(low):
            raise ValueError('Rentang assessment Argus tidak valid')
        return {'label': label, 'basis': basis, 'low': low, 'high': high, 'unit': 'USD/MT',
                'date': date.date().isoformat(), 'page': 2, 'source_file': path.name,
                'source_sha256': digest, 'product': 'urea_granular'}

    cfr = {country: record for country, label in ARGUS_CFR.items() if (record := find(label, 'CFR'))}
    cfr_ports = {port: record for port, label in ARGUS_PORT_CFR.items() if (record := find(label, 'CFR'))}
    north_africa = find('North Africa full range', 'FOB')
    regional = {'Libya': north_africa, 'Algeria': north_africa, 'Egypt': north_africa} if north_africa else {}
    global_fob = find('Southeast Asia', 'FOB')
    return {'cfr': cfr, 'cfr_ports': cfr_ports, 'regional_fob': regional, 'global_fob': global_fob,
            'source': path.name, 'date': date.date().isoformat()}


def read_comparables(root: Path) -> dict:
    files = list((root / 'public').glob('Fertecon*Nitrogen*.pdf'))
    candidates = []
    for path in files:
        text = _text(path, 0)
        found = re.search(r'Volume\s+\d+\s*/\s*Issue\s+\d+\s*/\s*(\w+\s+\d{1,2},\s*\d{4})', text)
        if found:
            candidates.append((datetime.strptime(found.group(1), '%B %d, %Y'), path))
    if not candidates:
        raise ValueError('Laporan Fertecon dengan tanggal yang terbaca belum tersedia')
    latest = max(date for date, _ in candidates)
    choices = [path for date, path in candidates if date == latest]
    if len({sha256(path.read_bytes()).hexdigest() for path in choices}) != 1:
        raise ValueError('Ada beberapa laporan berbeda pada tanggal yang sama')
    path = choices[0]
    from copy import deepcopy
    return deepcopy(_read_report(str(path.resolve()), sha256(path.read_bytes()).hexdigest()))


@lru_cache(maxsize=8)
def _read_report(filename: str, digest: str) -> dict:
    path = Path(filename)
    if sha256(path.read_bytes()).hexdigest() != digest:
        raise ValueError('Laporan berubah saat dibaca')
    page1, page2 = _text(path, 0), _text(path, 1)
    match = re.search(r'Volume\s+\d+\s*/\s*Issue\s+\d+\s*/\s*(\w+\s+\d{1,2},\s*\d{4})', page1)
    if not match:
        raise ValueError('Tanggal laporan Fertecon tidak dikenali')
    date = datetime.strptime(match.group(1), '%B %d, %Y').date().isoformat()
    records = {}
    for country, (label, code) in COUNTRIES.items():
        page = page2 if country == 'Brazil' else page1
        line = next((line for line in page.splitlines() if label in line and code in line), '')
        tail = line.split(code, 1)[-1].strip() if line else ''
        number = r'(\d+(?:\.\d+)?)'
        value = re.match(r'(?:[–-]\s*)?' + number + r'(?:\s*[–-]\s*' + number + r')?', tail)
        if value:
            records[country] = {'label': label, 'low': value.group(1), 'high': value.group(2) or value.group(1),
                                'page': 2 if country == 'Brazil' else 1, 'date': date, 'code': code}
    label, code = 'CFR SE Asia urea (granular)', 'FGUAC04'
    line = next((line for line in page1.splitlines() if label in line and code in line), '')
    match = re.search(r'FGUAC04\s+[–-]\s*(\d+(?:\.\d+)?)\s*[–-]\s*(\d+(?:\.\d+)?)', line)
    if match:
        for country in ('Indonesia', 'Malaysia', 'Singapore', 'Brunei'):
            records[country] = {'label': label, 'low': match.group(1), 'high': match.group(2),
                                'page': 1, 'date': date, 'code': code}
    fob_line = next((line for line in page1.splitlines() if 'FOB SE Asia urea (granular)' in line and 'FGUAA04' in line), '')
    fob_match = re.search(r'FGUAA04\s+[–-]\s*(\d+(?:\.\d+)?)\s*[–-]\s*(\d+(?:\.\d+)?)', fob_line)
    global_fob = {'label': 'FOB SE Asia urea (granular)', 'low': fob_match.group(1), 'high': fob_match.group(2),
                  'date': date, 'page': 1, 'basis': 'FOB', 'unit': 'USD/MT'} if fob_match else None
    start = page2.find('Platts Fertecon dry bulk fertilizer freight assessments')
    end = page2.find('Nitrates', start)
    if start < 0 or end < 0:
        raise ValueError('Tabel freight Fertecon tidak dikenali')
    voyage = []
    pattern = re.compile(r'^(.+?)\s*[–-]\s*(.+?)\s*\((\d+)kt\)\s+(\w+)\s+\S+\s+(\d+(?:\.\d+)?)\s*[–-]\s*(\d+(?:\.\d+)?)')
    for line in page2[start:end].splitlines():
        m = pattern.match(line.strip())
        if m:
            voyage.append({'origin': m[1].strip(), 'destination': m[2].strip(), 'cargo_mt': int(m[3]) * 1000,
                           'code': m[4], 'low': m[5], 'high': m[6], 'date': date, 'page': 2})
    for record in [*records.values(), *voyage, *([global_fob] if global_fob else [])]:
        lo, hi = Decimal(record['low']), Decimal(record['high'])
        if not lo.is_finite() or not hi.is_finite() or lo <= 0 or hi < lo:
            raise ValueError('Rentang assessment tidak valid')
        record.update(unit='USD/MT', source_sha256=digest, source_file=path.name,
                      product='urea_granular' if 'label' in record else 'dry_bulk_fertilizer')
    return {'cfr': records, 'voyages': voyage, 'global_fob': global_fob, 'source': path.name, 'date': date, 'sha256': digest,
            'coverage': {'cfr_countries': sorted(records), 'freight_routes': len(voyage)}}


def destination_country(root: Path, port_name: str) -> str | None:
    from pilog_cfr_dss.sources.route_distance import ports
    matches = [country for name, country in ports(root / 'data/raw/Ports.xlsx') if name.casefold() == port_name.casefold()]
    return matches[0] if len(matches) == 1 else None


def voyage_matches(records: list[dict], origin: str, destination: str) -> list[dict]:
    """Return best available route context; annotate route differences."""
    origins = {'Jubail': {'Middle East'}, 'Mesaieed': {'Middle East'},
               'Sur': {'Middle East'}, 'Zhanjiang': {'South China'},
               'Klaipeda': {'Baltic'}, 'Gdansk': {'Baltic'},
               'Novorossiysk': {'Black Sea'}, 'Constanta': {'Black Sea'}}
    destinations = {'Mundra': {'West Coast India'}, 'Santos': {'Brazil'},
                    'Jorf Lasfar': {'Morocco'}, 'Arzew': {'Morocco'},
                    'Damietta': {'Morocco'}, 'Mersa Al Brega': {'Morocco'},
                    'Bangkok': {'Thailand'}}
    candidates = [r for r in records if r['destination'] in destinations.get(destination, set())]
    matches = [dict(r, match_scope='rute_kawasan') for r in candidates if r['origin'] in origins.get(origin, set())]
    if matches:
        return matches
    # User requested broad regional context. Do not present a route with a
    # different origin as if it were a comparable quote, or calculate a gap.
    if candidates:
        return [dict(r, match_scope='tujuan_kawasan_asal_berbeda') for r in candidates]
    origins_only = [r for r in records if r['origin'] in origins.get(origin, set())]
    if origins_only:
        return [dict(r, match_scope='asal_kawasan_tujuan_berbeda') for r in origins_only]
    return [dict(r, match_scope='rute_global_berbeda') for r in records]


