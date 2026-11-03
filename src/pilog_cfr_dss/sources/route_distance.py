"""Port catalog and one-way indicative sea distance; never infer missing ports."""
from functools import lru_cache
from pathlib import Path
from decimal import Decimal
import json
import re
import unicodedata
import hashlib
from threading import Lock
from time import monotonic, sleep
from openpyxl import load_workbook
from pilog_cfr_dss.sources.od_distance import read_distance

_request_lock = Lock()
_last_request = 0.0


def ports(path: Path):
    wb = load_workbook(path, read_only=True, data_only=True)
    try:
        rows = list(wb.active.values)
    finally:
        wb.close()
    if tuple(rows[0][:2]) != ('Country', 'Primary Port'):
        raise ValueError('INVALID_PORT_CATALOG')
    found = set()
    for country, port, *_ in rows[1:]:
        if country and port:
            found.add((str(port).strip(), str(country).strip()))
    return sorted(found, key=lambda x: (x[0].casefold(), x[1].casefold()))


@lru_cache(maxsize=256)
def geocode_port(port: str, country: str):
    from geopy.geocoders import Nominatim
    import pycountry
    global _last_request
    geocoder = Nominatim(user_agent='pilog-cfr-dss-demo/1.0', timeout=8)
    query = f'Port {port}, {country}'
    with _request_lock:
        sleep(max(0, 1.05 - (monotonic() - _last_request)))
        try:
            locations = geocoder.geocode(query, exactly_one=False, limit=8, addressdetails=True)
        finally:
            _last_request = monotonic()
    aliases = {'South Korea':'KR','Russia':'RU','Vietnam':'VN','Taiwan':'TW','Turkey':'TR',
               'Brunei':'BN','Venezuela':'VE','United Kingdom':'GB','United States':'US','Libya':'LY'}
    try:
        country_code = (aliases.get(country) or pycountry.countries.lookup(country).alpha_2).lower()
    except LookupError:
        raise ValueError('PORT_COUNTRY_UNRESOLVED') from None
    def norm(value):
        value = unicodedata.normalize('NFKD', str(value)).encode('ascii','ignore').decode().lower()
        return re.sub(r'[^a-z0-9]+',' ',value).strip()
    candidates=[]
    for item in locations or []:
        raw=item.raw; category=str(raw.get('class','')).lower(); typ=str(raw.get('type','')).lower()
        address=raw.get('address') or {}; label=norm(raw.get('display_name') or getattr(item, 'address', ''))
        port_named = bool(re.search(r'\b(port|harbour|harbor|pelabuhan)\b',label))
        port_type = typ in {'port','harbour','harbor','dock','terminal'} or (typ=='industrial' and category in {'landuse','industrial'} and port_named)
        if (address.get('country_code','').lower()==country_code and port_type and port_named
                and norm(port) in label and category not in {'office','shop','tourism'}):
            candidates.append(item)
    if not candidates:
        raise ValueError('PORT_NOT_FOUND')
    if len(candidates)!=1:
        raise ValueError('PORT_LOCATION_AMBIGUOUS')
    return (float(candidates[0].longitude), float(candidates[0].latitude))


def catalog_coordinate(catalog: Path, port: str, country: str):
    confirmed_file=catalog.parent/'confirmed_port_locations.json'
    if confirmed_file.exists():
        raw_confirmed=confirmed_file.read_bytes()
        confirmed=json.loads(raw_confirmed.decode('utf-8'))['confirmed']
        selected=[x for x in confirmed if x['port'].casefold()==port.casefold() and x['country'].casefold()==country.casefold()]
        if len(selected)>1:
            raise ValueError('CONFIRMED_PORT_NOT_UNIQUE')
        if selected:
            entry=selected[0]; coords=entry['coordinates']
            if len(coords)!=2 or not -180 <= coords[0] <= 180 or not -90 <= coords[1] <= 90:
                raise ValueError('INVALID_CATALOG_COORDINATES')
            return tuple(coords), entry['locode'], entry['coordinate_source'], hashlib.sha256(raw_confirmed).hexdigest()
    if not catalog.exists():
        return None
    raw=catalog.read_bytes(); data=json.loads(raw.decode('utf-8'))
    found=[x for x in data['matched'] if x['port'].casefold()==port.casefold() and x['country'].casefold()==country.casefold()]
    if len(found)!=1:
        return None
    entry=found[0]; coords=entry['coordinates']
    if len(coords)!=2 or not -180 <= coords[0] <= 180 or not -90 <= coords[1] <= 90:
        raise ValueError('INVALID_CATALOG_COORDINATES')
    return tuple(coords), entry['locode'], entry['coordinate_source'], hashlib.sha256(raw).hexdigest()


@lru_cache(maxsize=256)
def searoute_port_coordinate(port: str, country: str):
    """Match a unique exact port name and country in the installed port catalog."""
    import searoute
    import pycountry
    aliases = {'South Korea':'KR','Russia':'RU','Vietnam':'VN','Taiwan':'TW','Turkey':'TR',
               'Brunei':'BN','Venezuela':'VE','United Kingdom':'GB','United States':'US','Libya':'LY'}
    try:
        code = aliases.get(country) or pycountry.countries.lookup(country).alpha_2
    except LookupError:
        return None
    graph=searoute.setup_P()
    matches=[(node,attrs) for node,attrs in graph.nodes(data=True)
             if str(attrs.get('name','')).strip().casefold()==port.strip().casefold()
             and str(attrs.get('cty','')).strip().casefold()==country.strip().casefold()
             and str(attrs.get('port','')).upper().startswith(code)]
    alias_hash = None
    if not matches:
        alias_file=Path(__file__).resolve().parents[3]/'data/processed/port_name_aliases.json'
        if alias_file.exists():
            aliases_data=json.loads(alias_file.read_text(encoding='utf-8')).get('aliases',[])
            candidates=[entry for entry in aliases_data if entry['port'].casefold()==port.casefold() and entry['country'].casefold()==country.casefold() and entry['locode'].startswith(code)]
            if len(candidates)==1:
                locode=candidates[0]['locode']
                matches=[(node,attrs) for node,attrs in graph.nodes(data=True) if attrs.get('port')==locode]
                alias_hash=hashlib.sha256(alias_file.read_bytes()).hexdigest()
    if len(matches)!=1:
        return None
    point,attrs=matches[0]; locode=attrs['port']
    if sum(1 for _,a in graph.nodes(data=True) if a.get('port')==locode)!=1:
        return None
    return tuple(point), locode, ('Searoute 1.6.0 + approved name alias' if alias_hash else 'Searoute 1.6.0 port catalog'), alias_hash


@lru_cache(maxsize=512)
def _sea_route(origin, destination):
    import searoute
    result = searoute.searoute(origin, destination, units='naut')
    value = Decimal(str(result.properties['length']))
    if not value.is_finite() or value <= 0:
        raise ValueError('INVALID_ROUTE_DISTANCE')
    return str(value)


def distance(origin, destination, workbook: Path, product='urea granular bulk', catalog: Path | None=None):
    if origin == destination:
        raise ValueError('SAME_PORT')
    try:
        catalog = catalog or workbook.parent.parent/'processed/port_locations_unlocode.json'
        first = catalog_coordinate(catalog, *origin) or searoute_port_coordinate(*origin)
        second = catalog_coordinate(catalog, *destination) or searoute_port_coordinate(*destination)
        a = first[0] if first else geocode_port(*origin)
        b = second[0] if second else geocode_port(*destination)
        return {'value': _sea_route(a, b), 'unit': 'NM', 'loading_port': origin[0],
                'discharging_port': destination[0], 'source_status': 'estimated_sea_route',
                'source_reference': 'Estimasi jarak laut', 'provider': 'UN/LOCODE / Nominatim + Searoute', 'origin_coordinates': a,
                'destination_coordinates': b, 'origin_locode':first[1] if first else None,
                'destination_locode':second[1] if second else None,
                'origin_coordinate_source':first[2] if first else 'OpenStreetMap Nominatim',
                'destination_coordinate_source':second[2] if second else 'OpenStreetMap Nominatim',
                'port_catalog_sha256':(first[3] if first else None) or (second[3] if second else None),
                'origin_catalog_sha256':first[3] if first else None,
                'destination_catalog_sha256':second[3] if second else None,
                'coordinates_scope':'indicative_not_berth'}
    except Exception as error:
        try:
            result = read_distance(workbook, origin[0], destination[0], product)
            result['fallback_reason'] = type(error).__name__
            return result
        except (ValueError, KeyError, OSError):
            raise ValueError('DISTANCE_UNAVAILABLE_ENTER_MANUALLY') from error
