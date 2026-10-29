from __future__ import annotations

import csv
import hashlib
import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

from pilog_cfr_dss.models.contracts import CaseSnapshot, QualityResult


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _slug(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", label.strip().lower()).strip("_")


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def load_snapshot(dataset_path: Path, catalog_path: Path, manual_path: Path) -> CaseSnapshot:
    dataset = _rows(dataset_path)
    catalog = _rows(catalog_path)
    if any(_slug(row["Variable"]) == "voyage_expense_allocation_quantity_mt" for row in dataset):
        raise ValueError("OBSOLETE_ALLOCATION_QUANTITY")
    if not dataset or len(dataset) != len(catalog):
        raise ValueError("CATALOG_ROW_COUNT_MISMATCH")
    values: dict[str, Decimal | str | bool | None] = {}
    raw_rows: dict[str, dict] = {}
    for source, spec in zip(dataset, catalog, strict=True):
        if source["No"] != spec["no"] or _slug(source["Variable"]) != spec["canonical_key"]:
            raise ValueError(f"CATALOG_SOURCE_MISMATCH:{source.get('No')}")
        key = spec["canonical_key"]
        raw = source["Value"].strip()
        data_type = spec["data_type"]
        if data_type in {"decimal", "integer"}:
            try:
                value = Decimal(raw)
                if not value.is_finite():
                    raise InvalidOperation
                if data_type == "integer" and value != value.to_integral_value():
                    raise InvalidOperation
            except (InvalidOperation, ValueError):
                value = None
        elif data_type == "boolean":
            value = {"yes": True, "true": True, "no": False, "false": False}.get(raw.lower())
        else:
            value = raw
        values[key] = value
        raw_rows[key] = {
            "row": int(source["No"]), "label": source["Variable"], "raw_value": raw,
            "unit": spec["unit"], "currency": spec["currency"],
            "source_status": spec["source_status"],
        }
    manual = json.loads(manual_path.read_text(encoding="utf-8"))
    return CaseSnapshot(
        case_id=str(manual.get("case_id", "I2-UNNAMED")),
        dataset_sha256=_sha256(dataset_path),
        manual_sha256=_sha256(manual_path),
        origin=str(values.get("loading_port") or ""),
        destination=str(values.get("discharging_port") or ""),
        values=values,
        raw_rows=raw_rows,
        manual=manual,
    )


CRITICAL_POSITIVE = (
    "laden_distance_nm", "ballast_distance_nm", "laden_speed_knots",
    "ballast_speed_knots", "dwcc_cargo_quantity_mt", "loading_rate_mt_day",
    "discharge_rate_mt_day", "fuel_oil_price_usd_mt", "diesel_oil_price_usd_mt",
    "dwt_mt", "freight_rate_usd_mt",
)

CRITICAL_NONNEGATIVE = (
    "fuel_oil_consumption_laden_mt_day", "fuel_oil_consumption_ballast_mt_day",
    "diesel_consumption_at_sea_laden_mt_day", "diesel_consumption_at_sea_ballast_mt_day",
    "auxiliary_engine_power_kw", "in_port_diesel_factor_kg_kwh",
    "running_costs_usd_day", "other_voyage_costs_total_usd", "canal_transit_days",
)


def assess_quality(case: CaseSnapshot) -> QualityResult:
    checks: list[dict] = []

    def add(code: str, status: str, fields: list[str], detail: str) -> None:
        checks.append({"code": code, "status": status, "fields": fields, "detail": detail})

    missing_route = [name for name, value in (("loading_port", case.origin), ("discharging_port", case.destination)) if not value]
    add("ROUTE_IDENTITY", "BLOCK" if missing_route else "PASS", missing_route, "Origin dan destination dari dataset")
    bad_numeric = [key for key in CRITICAL_POSITIVE if not isinstance(case.values.get(key), Decimal) or case.values[key] <= 0]
    add("CRITICAL_NUMERIC", "BLOCK" if bad_numeric else "PASS", bad_numeric, "Input fisik minimum harus positif")
    bad_nonnegative = [key for key in CRITICAL_NONNEGATIVE if not isinstance(case.values.get(key), Decimal) or case.values[key] < 0]
    add("CRITICAL_NONNEGATIVE", "BLOCK" if bad_nonnegative else "PASS", bad_nonnegative, "Biaya dan konsumsi yang diperlukan tidak boleh negatif")
    factor = case.values.get("in_port_working_load_factor")
    add("PORT_LOAD_FACTOR", "BLOCK" if not isinstance(factor, Decimal) or not Decimal(0) <= factor <= Decimal(1) else "PASS",
        ["in_port_working_load_factor"] if not isinstance(factor, Decimal) or not Decimal(0) <= factor <= Decimal(1) else [],
        "Faktor beban pelabuhan harus berada pada 0..1")
    commission_keys = ("freight_commission_rate", "broker_fee_rate", "additional_commission_rate")
    commission_values = [case.values.get(key) for key in commission_keys]
    bad_commission = [key for key, value in zip(commission_keys, commission_values) if not isinstance(value, Decimal) or not Decimal(0) <= value < Decimal(1)]
    if not bad_commission and sum(commission_values, Decimal(0)) >= Decimal(1):
        bad_commission = list(commission_keys)
    add("COMMISSION_RATE", "BLOCK" if bad_commission else "PASS", bad_commission, "Komisi harus berupa fraksi nonnegatif dengan total kurang dari 1")
    bad_optional = [key for key, row in case.raw_rows.items() if row["raw_value"] and case.values[key] is None]
    add("OPTIONAL_PARSE", "WARN" if bad_optional else "PASS", bad_optional, "Nilai opsional tidak dapat dibaca")
    price_missing = []
    for name in ("index", "alpha", "cfr_adjustment"):
        item = case.manual.get("pricing", {}).get(name, {})
        try:
            numeric = Decimal(str(item.get("value")))
            if not numeric.is_finite():
                raise InvalidOperation
        except (InvalidOperation, TypeError, ValueError):
            price_missing.append(f"pricing.{name}.value")
        if item.get("unit") != "USD/MT":
            price_missing.append(f"pricing.{name}.unit_USD_MT")
    adjustment = case.manual.get("pricing", {}).get("cfr_adjustment", {})
    if not adjustment.get("reason"):
        price_missing.append("pricing.cfr_adjustment.reason")
    add("CONTROLLED_PRICING", "BLOCK" if price_missing else "PASS", price_missing, "Index, Alpha, dan adjustment harus bernilai numerik dengan unit USD/MT; adjustment punya alasan")
    add("SOURCE_METADATA_DEFERRED", "WARN", ["source", "as_of", "owner"], "Sumber/as-of/approval domain belum menjadi Gate pada simulasi ini")
    status = "BLOCK" if any(x["status"] == "BLOCK" for x in checks) else "WARN" if any(x["status"] == "WARN" for x in checks) else "PASS"
    return QualityResult(status, tuple(checks))
