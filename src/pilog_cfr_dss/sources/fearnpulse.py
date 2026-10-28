"""Public Fearnpulse observations, immutable payloads, explicit units/dates.

These are the read-only operations used by the public site, not a licensed
integration guarantee. No cookies, browser account, credentials or mutations.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen
from uuid import uuid4

from pilog_cfr_dss.validation.iteration_04 import number, timestamp

GRAPHQL = "https://hasura.fearnpulse.com/v1/graphql"
REPORT_QUERY = """query GetReportsToDateByLimit($dateTo: timestamptz, $report_name: String, $limit: Int) {
 report(where: {created_at: {_lte: $dateTo}, report_name: {_eq: $report_name}}, limit: $limit, order_by: {created_at: desc}) {
 created_at id report_name }
}"""
RATES_QUERY = """query GetRatesByMetaByRange($routes: [String!], $rateTypes: [String!], $rateSubtypes: [String!], $dateFrom: date, $dateTo: date) {
 rate_meta(where: {info: {route: {_in: $routes}, rate_type: {_in: $rateTypes}, rate_subtype: {_in: $rateSubtypes}}, rate_unit: {_eq: "usd"}}) {
 rates(where: {date: {_gte: $dateFrom, _lte: $dateTo}}, order_by: {date: desc}) {date rate}
 info {route rate_type rate_subtype} }
}"""
ROUTES = {"Supramax": "Supramax (58 000 dwt)", "Handysize": "Handysize (38 000 dwt)"}
BUNKERS = {"fo_price_usd_mt": (306, "Singapore 380 CST"), "do_price_usd_mt": (307, "Singapore MGO")}


def _decode(raw: str):
    return json.loads(raw, parse_float=Decimal)


def _positive(value, field):
    result = number(value, field)
    if result <= 0:
        raise ValueError("MISSING_OR_ZERO_MARKET_RATE:" + field)
    return str(result)


def normalize_payloads(raw: dict[str, str], fetched_at: str) -> dict:
    timestamp(fetched_at)
    report_data = _decode(raw["fearnpulse_report.json"])
    reports = report_data.get("data", {}).get("report", [])
    if report_data.get("errors") or not reports:
        raise ValueError("FEARNPULSE_REPORT_UNAVAILABLE")
    report = reports[0]
    published = timestamp(report["created_at"])
    rates_data = _decode(raw["fearnpulse_tc.json"])
    if rates_data.get("errors"):
        raise ValueError("FEARNPULSE_RATE_QUERY_ERROR")
    tc = {}
    for row in rates_data.get("data", {}).get("rate_meta", []):
        info = row.get("info", {})
        family = next((key for key, route in ROUTES.items() if info.get("route") == route), None)
        if family is None:
            continue
        if info.get("rate_type") != "BULK" or info.get("rate_subtype") != "TC":
            raise ValueError("FEARNPULSE_SERIES_BASIS_MISMATCH")
        candidates = row.get("rates", [])
        if not candidates:
            raise ValueError("FEARNPULSE_EMPTY_TC_SERIES:" + family)
        latest = max(candidates, key=lambda x: x["date"])
        observed = datetime.fromisoformat(latest["date"]).date().isoformat()
        if observed > published.date().isoformat() or family in tc:
            raise ValueError("FEARNPULSE_AMBIGUOUS_TC_SERIES")
        tc[family] = {"value": _positive(latest["rate"], family), "unit": "USD/day",
            "series": ROUTES[family], "contract_period": "1_year_TC", "source_observed_on": observed,
            "source_status": "observed_public_market", "source_reference": "https://fearnpulse.com/#2 :: 1 Year T/C :: " + family,
            "commission_basis": "not_stated_by_source"}
    if set(tc) != set(ROUTES):
        raise ValueError("FEARNPULSE_MISSING_REQUIRED_CLASS")
    bunkers = {}
    for key, (series_id, name) in BUNKERS.items():
        payload = _decode(raw[f"fearnpulse_{series_id}.json"])
        columns = payload.get("columns", [])
        if not {"tsid", "value", "date"}.issubset(columns):
            raise ValueError("FEARNPULSE_TS_SCHEMA_CHANGED")
        source_rows = payload.get("data", [])
        if not isinstance(source_rows, list) or any(not isinstance(row, list) or len(row) != len(columns) for row in source_rows):
            raise ValueError("FEARNPULSE_MALFORMED_TS_ROW")
        rows = [dict(zip(columns, row)) for row in source_rows]
        if not rows or any(row["tsid"] != series_id for row in rows):
            raise ValueError("FEARNPULSE_INVALID_BUNKER_SERIES")
        latest = max(rows, key=lambda x: x["date"])
        milliseconds = number(latest["date"], "source epoch")
        if milliseconds != milliseconds.to_integral_value():
            raise ValueError("FEARNPULSE_INVALID_EPOCH")
        seconds, remainder = divmod(int(milliseconds), 1000)
        observed = datetime.fromtimestamp(seconds, tz=timezone.utc) + timedelta(milliseconds=remainder)
        bunkers[key] = {"value": _positive(latest["value"], name), "unit": "USD/MT", "series": name,
            "series_id": series_id, "source_observed_on": observed.date().isoformat(),
            "source_observed_at": observed.isoformat(), "source_timestamp_kind": "daily_series_epoch_not_trade_execution",
            "source_status": "observed_public_market", "source_reference": "https://fearnpulse.com/#6 :: " + name}
    return {"snapshot_version": "FP.1", "snapshot_id": "fp_" + uuid4().hex,
        "provider": "Fearnpulse / Fearnleys", "url": "https://fearnpulse.com/", "fetched_at": fetched_at,
        "report_published_at": published.isoformat(), "report_id": report["id"],
        "tc_rates": tc, "bunkers": bunkers, "raw_payloads": raw,
        "payload_hashes": {name: hashlib.sha256(content.encode("utf-8")).hexdigest() for name, content in raw.items()}}


def _request(url, payload=None):
    content = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(url, data=content, headers={"User-Agent": "Mozilla/5.0 PILOG-CFR-DSS/1.0",
        "Accept": "application/json", "Content-Type": "application/json", "Referer": "https://fearnpulse.com/"})
    # One bounded retry; failure never becomes a made-up quote or a zero.
    for attempt in range(2):
        try:
            with urlopen(request, timeout=12) as response:
                return response.read().decode("utf-8")
        except OSError:
            if attempt:
                raise


def fetch_snapshot() -> dict:
    now = datetime.now(timezone.utc)
    raw = {"fearnpulse_report.json": _request(GRAPHQL, {"operationName": "GetReportsToDateByLimit", "query": REPORT_QUERY,
        "variables": {"dateTo": now.isoformat(), "report_name": "Fearnleys Weekly Report", "limit": 1}})}
    reports = _decode(raw["fearnpulse_report.json"]).get("data", {}).get("report", [])
    if not reports:
        raise ValueError("FEARNPULSE_REPORT_UNAVAILABLE")
    published = timestamp(reports[0]["created_at"])
    date_to = published.date().isoformat()
    raw["fearnpulse_tc.json"] = _request(GRAPHQL, {"operationName": "GetRatesByMetaByRange", "query": RATES_QUERY,
        "variables": {"routes": list(ROUTES.values()), "rateTypes": ["BULK"], "rateSubtypes": ["TC"],
                      "dateFrom": (published.date() - timedelta(days=30)).isoformat(), "dateTo": date_to}})
    def bunker(entry):
        series_id, _ = entry
        return f"fearnpulse_{series_id}.json", _request(f"https://fearnpulse.com/api/marketapi/TS?last=2&id={series_id}&date_to={date_to}")
    with ThreadPoolExecutor(max_workers=2) as pool:
        raw.update(dict(pool.map(bunker, BUNKERS.values())))
    return normalize_payloads(raw, datetime.now(timezone.utc).isoformat())


def save_snapshot(snapshot: dict, root: Path) -> Path:
    raw_dir = root / "data/raw/fearnpulse" / snapshot["snapshot_id"]
    raw_dir.mkdir(parents=True, exist_ok=False)
    for name, content in snapshot["raw_payloads"].items():
        if Path(name).name != name:
            raise ValueError("INVALID_MARKET_PAYLOAD_PATH")
        (raw_dir / name).write_text(content, encoding="utf-8")
    path = root / "data/processed" / (snapshot["snapshot_id"] + ".json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def latest_saved(root: Path) -> dict | None:
    paths = list((root / "data/processed").glob("fp_*.json"))
    if not paths:
        return None
    snapshots = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    return max(snapshots, key=lambda x: timestamp(x["fetched_at"]))
