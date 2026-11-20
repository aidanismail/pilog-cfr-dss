"""KOBC public daily dry-bulk assessments; no invented route mappings."""
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from threading import Lock
from uuid import uuid4
from zoneinfo import ZoneInfo
import json
import requests

URLS = {
    "Handysize": "https://www.kobc.or.kr/ebz/shippinginfo/handy/gridList.do?mId=0301000000",
    "Supramax": "https://www.kobc.or.kr/ebz/shippinginfo/supramax/gridList.do?mId=0301000000",
}
STANDARD = "https://www.kobc.or.kr/ebz/shippinginfo/kdci/gridList.do?mId=0301000000"
HEADERS = {"Handysize": ["Date", "MH1", "MH2", "MH3", "MH4", "MH5", "TC Average"],
           "Supramax": ["Date", "MS1", "MS2", "MS4", "MS5", "MS6", "MS7", "TC Average"]}
_cache_lock = Lock()


class _Tables(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables, self.table, self.row, self.cell = [], None, None, None

    def handle_starttag(self, tag, attrs):
        if tag == "table" and self.table is None:
            self.table = []
        elif self.table is not None and tag == "tr":
            self.row = []
        elif self.row is not None and tag in ("th", "td"):
            self.cell = []

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ("th", "td") and self.cell is not None:
            self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.table.append(self.row)
            self.row = None
        elif tag == "table" and self.table is not None:
            self.tables.append(self.table)
            self.table = None


def parse_table(html, family, today):
    parser = _Tables()
    parser.feed(html)
    matches = [t for t in parser.tables if t and t[0] == HEADERS[family]]
    if len(matches) != 1:
        raise ValueError("KOBC_TABLE_HEADER_MISMATCH")
    candidates = []
    for row in matches[0][1:]:
        if len(row) != len(HEADERS[family]):
            continue
        try:
            day = date.fromisoformat(row[0])
        except ValueError:
            continue
        if not 0 <= (today - day).days <= 7:
            continue
        values = {}
        for key, raw in zip(HEADERS[family][1:], row[1:]):
            try:
                n = Decimal(raw.replace(",", ""))
                if n.is_finite() and n > 0:
                    values[key] = str(n)
            except InvalidOperation:
                pass
        if "TC Average" in values:
            candidates.append((day, values))
    if not candidates:
        raise ValueError("KOBC_NO_FRESH_VALID_DATA")
    day, values = max(candidates, key=lambda x: x[0])
    if sum(1 for candidate_day, _ in candidates if candidate_day == day) != 1:
        raise ValueError("KOBC_DUPLICATE_DATE")
    return {"observed_on": day.isoformat(), "values": values, "unit": "USD/day",
            "source_url": URLS[family], "standard_url": STANDARD,
            "source_family": family, "commission_basis": "KOBC standard: 5% total commission",
            "benchmark_dwt_mt": 33000 if family == "Handysize" else 58000}


def fetch_snapshot(now=None):
    now = now or datetime.now(timezone.utc)
    today = now.astimezone(ZoneInfo("Asia/Seoul")).date()
    snapshots, errors = {}, {}
    for family, url in URLS.items():
        try:
            response = requests.get(url, timeout=8, headers={"User-Agent": "PILOG-Freight-Desk/1.0"})
            response.raise_for_status()
            if len(response.content) > 2_000_000:
                raise ValueError("KOBC_RESPONSE_TOO_LARGE")
            snapshots[family] = parse_table(response.text, family, today)
            snapshots[family]["fetched_at"] = now.isoformat()
        except (requests.RequestException, ValueError) as error:
            errors[family] = str(error)
    return {"provider": "KOBC", "fetched_at": now.isoformat(), "classes": snapshots, "errors": errors}


def remember_snapshot(incoming, folder):
    """Keep the newest observation independently for each class across page reloads."""
    path = folder / "kobc_latest.json"
    with _cache_lock:
        classes = {}
        try:
            cached = json.loads(path.read_text(encoding="utf-8"))
            for family, quote in cached["classes"].items():
                if family in URLS and quote["source_url"] == URLS[family] and quote["unit"] == "USD/day":
                    date.fromisoformat(quote["observed_on"])
                    datetime.fromisoformat(quote["fetched_at"])
                    value = Decimal(quote["values"]["TC Average"])
                    if value.is_finite() and value > 0:
                        classes[family] = quote
        except (OSError, ValueError, KeyError, TypeError, AttributeError, InvalidOperation):
            pass
        for family, quote in incoming["classes"].items():
            previous = classes.get(family)
            if previous is None or (quote["observed_on"], quote["fetched_at"]) >= (
                    previous["observed_on"], previous["fetched_at"]):
                classes[family] = quote
        if incoming["classes"]:
            temporary = folder / ("kobc_" + uuid4().hex + ".tmp")
            try:
                folder.mkdir(parents=True, exist_ok=True)
                temporary.write_text(json.dumps({"classes": classes}, allow_nan=False), encoding="utf-8")
                temporary.replace(path)
            except OSError:
                pass
            finally:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass
    return dict(incoming, classes=classes)


def select_assessment(snapshot, family, load, discharge, today):
    """Conservative route match; otherwise KOBC class TC average."""
    data = snapshot.get("classes", {}).get(family)
    if not data or data.get("unit") != "USD/day":
        return None
    try:
        age = (today - date.fromisoformat(data["observed_on"])).days
    except (TypeError, ValueError, KeyError):
        return None
    if not 0 <= age <= 7:
        return None
    origin = (load.get("name", "").casefold(), load.get("country", "").casefold())
    destination = (discharge.get("name", "").casefold(), discharge.get("country", "").casefold())
    code, description, scope = "TC Average", "Rata-rata kelas KOBC", "class_average"
    # KOBC standard MS5: S.China delivery, South/East Kalimantan loading,
    # Haldia–Tuticorin redelivery. This narrow mapping is not an exact fixture.
    if family == "Supramax" and origin == ("bontang", "indonesia") and destination in {
            ("haldia", "india"), ("tuticorin", "india")} and "MS5" in data["values"]:
        code, description, scope = "MS5", "S.China–Indonesia–East India", "route_reference"
    elif family == "Supramax" and origin == ("bontang", "indonesia") and destination == ("ningbo", "china") and "MS6" in data["values"]:
        code, description, scope = "MS6", "S.China–Indonesia–S.China", "route_reference"
    elif family == "Handysize" and origin == ("bontang", "indonesia") and destination == ("qingdao", "china") and "MH3" in data["values"]:
        code, description, scope = "MH3", "S.China–Southeast Asia–Northeast Asia", "route_reference"
    value = data["values"].get(code)
    if not value:
        return None
    return dict(data, value=value, code=code, description=description, scope=scope)
