"""Strict, source-labelled Iteration 3 simulation inputs (not an I2 loader)."""

from __future__ import annotations

import csv
import hashlib
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from pilog_cfr_dss.models.contracts import CaseSnapshot


TEXT_UNITS = {"cargo_description": "text", "loading_port": "port", "discharging_port": "port"}
NUMERIC_UNITS = {
    "laden_distance_nm": "NM", "ballast_distance_nm": "NM",
    "laden_speed_knots": "knot", "ballast_speed_knots": "knot",
    "fuel_oil_consumption_laden_mt_day": "MT/day",
    "fuel_oil_consumption_ballast_mt_day": "MT/day",
    "diesel_consumption_at_sea_laden_mt_day": "MT/day",
    "diesel_consumption_at_sea_ballast_mt_day": "MT/day",
    "in_port_working_load_factor": "fraction",
    "in_port_diesel_factor_kg_kwh": "kg/kWh",
    "auxiliary_engine_power_kw": "kW", "dwt_mt": "MT",
    "bunkers_allowance_mt": "MT", "constants_allowance_mt": "MT",
    "dwcc_cargo_quantity_mt": "MT", "loading_rate_mt_day": "MT/day",
    "discharge_rate_mt_day": "MT/day", "canal_transit_days": "day",
    "fuel_oil_price_usd_mt": "USD/MT", "diesel_oil_price_usd_mt": "USD/MT",
    "other_voyage_costs_total_usd": "USD", "freight_rate_usd_mt": "USD/MT",
    "freight_commission_rate": "fraction", "running_costs_usd_day": "USD/day",
    "broker_fee_rate": "fraction", "additional_commission_rate": "fraction",
}
POSITIVE = {
    "laden_distance_nm", "ballast_distance_nm", "laden_speed_knots", "ballast_speed_knots",
    "auxiliary_engine_power_kw", "dwt_mt", "dwcc_cargo_quantity_mt",
    "loading_rate_mt_day", "discharge_rate_mt_day", "fuel_oil_price_usd_mt",
    "diesel_oil_price_usd_mt", "freight_rate_usd_mt",
}
FRACTIONS = {"in_port_working_load_factor", "freight_commission_rate", "broker_fee_rate", "additional_commission_rate"}
ALLOWED_SOURCE_STATUS = {"confirmed_case", "inherited_experimental"}


def decimal(value: Any, key: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise ValueError(f"INVALID_NUMBER:{key}") from error
    if not result.is_finite():
        raise ValueError(f"INVALID_NUMBER:{key}")
    return result


def _required_synthetic(record: dict[str, Any], key: str) -> None:
    if record.get("source_status") != "simulation_only_synthetic":
        raise ValueError(f"MISSING_SIMULATION_LABEL:{key}")


def load_case(case_path: Path) -> tuple[CaseSnapshot, dict[str, Any], Path]:
    fixture = json.loads(case_path.read_text(encoding="utf-8"))
    if fixture.get("schema_version") != "I3.1" or fixture.get("mode") != "simulation":
        raise ValueError("INVALID_I3_CASE_VERSION_OR_MODE")
    relative = fixture.get("voyage_dataset")
    if not isinstance(relative, str) or Path(relative).name != relative:
        raise ValueError("INVALID_VOYAGE_DATASET_REFERENCE")
    dataset_path = case_path.parent / relative
    with dataset_path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    expected = set(TEXT_UNITS) | set(NUMERIC_UNITS)
    keys = [row.get("key", "") for row in rows]
    if len(keys) != len(expected) or set(keys) != expected or len(keys) != len(set(keys)):
        raise ValueError("I3_DATASET_KEY_MISMATCH")
    values: dict[str, Decimal | str | bool | None] = {}
    raw_rows: dict[str, dict[str, Any]] = {}
    for row_number, row in enumerate(rows, 2):
        key = row["key"]
        expected_unit = (TEXT_UNITS | NUMERIC_UNITS)[key]
        if row["unit"] != expected_unit:
            raise ValueError(f"INVALID_UNIT:{key}")
        if row["source_status"] not in ALLOWED_SOURCE_STATUS or not row["source_reference"]:
            raise ValueError(f"MISSING_LINEAGE:{key}")
        raw = row["value"].strip()
        if not raw:
            raise ValueError(f"MISSING_VALUE:{key}")
        value = raw if key in TEXT_UNITS else decimal(raw, key)
        if isinstance(value, Decimal):
            if (key in POSITIVE and value <= 0) or (key not in POSITIVE and value < 0):
                raise ValueError(f"INVALID_RANGE:{key}")
            if key in FRACTIONS - {"in_port_working_load_factor"} and value >= 1:
                raise ValueError(f"INVALID_FRACTION:{key}")
            if key == "in_port_working_load_factor" and value > 1:
                raise ValueError("INVALID_PORT_LOAD_FACTOR")
        values[key] = value
        raw_rows[key] = {**row, "row": row_number}
    if sum((values[key] for key in FRACTIONS - {"in_port_working_load_factor"}), Decimal(0)) >= 1:
        raise ValueError("INVALID_COMMISSION_SUM")
    if values["cargo_description"] != "UREA GRANULAR BULK" or values["loading_port"] != "Bontang":
        raise ValueError("INVALID_I3_COMMODITY_ORIGIN")
    if values["dwcc_cargo_quantity_mt"] != Decimal("45000"):
        raise ValueError("INVALID_I3_QUANTITY_BASIS")
    if not fixture.get("case_id"):
        raise ValueError("MISSING_CASE_ID")
    snapshot = CaseSnapshot(
        case_id=fixture["case_id"],
        dataset_sha256=hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        manual_sha256=hashlib.sha256(case_path.read_bytes()).hexdigest(),
        origin=str(values["loading_port"]), destination=str(values["discharging_port"]),
        values=values, raw_rows=raw_rows, manual=fixture,
    )
    return snapshot, fixture, dataset_path


def validate_commercial_fixture(fixture: dict[str, Any]) -> None:
    observations = fixture.get("market_index", {})
    if set(observations) != {"argus", "fertecon"}:
        raise ValueError("MISSING_INDEX_PUBLISHER")
    dates = set()
    for publisher, observation in observations.items():
        _required_synthetic(observation, publisher)
        if observation.get("unit") != "USD/MT" or observation.get("basis") != "FOB SEA granular":
            raise ValueError(f"INDEX_BASIS_MISMATCH:{publisher}")
        if not observation.get("series") or not observation.get("observation_date") or not observation.get("source_reference"):
            raise ValueError(f"MISSING_INDEX_METADATA:{publisher}")
        dates.add(observation["observation_date"])
        low, high = decimal(observation.get("low"), f"{publisher}.low"), decimal(observation.get("high"), f"{publisher}.high")
        if low <= 0 or high < low:
            raise ValueError(f"INVALID_INDEX_RANGE:{publisher}")
    if len(dates) != 1:
        raise ValueError("INDEX_DATE_MISMATCH")
    oe = fixture.get("oe_hps", {})
    _required_synthetic(oe, "oe_hps")
    if oe.get("unit") != "USD/MT" or decimal(oe.get("value"), "oe_hps") <= 0:
        raise ValueError("INVALID_OE_HPS")
    if not oe.get("source_reference"):
        raise ValueError("MISSING_OE_HPS_LINEAGE")
    assumptions = fixture.get("economic_assumptions", {})
    if assumptions != {
        "od_cost_method": "derived_voyage_proxy",
        "freight_selling_rate_basis": "i2_dataset_rate_for_simulation",
        "commission_basis": "gross_freight_revenue_cumulative",
        "vessel_mode": "owned", "source_status": "simulation_only_assumption",
    }:
        raise ValueError("UNCONFIRMED_ECONOMIC_ASSUMPTIONS")
    bids = fixture.get("bids")
    if not isinstance(bids, list) or not bids:
        raise ValueError("MISSING_BIDS")
    ids = set()
    for bid in bids:
        _required_synthetic(bid, "bid")
        if not bid.get("bid_id") or not bid.get("buyer_id") or not isinstance(bid.get("round"), int) or bid["round"] < 1:
            raise ValueError("INVALID_BID_ID_OR_ROUND")
        if bid["bid_id"] in ids:
            raise ValueError("DUPLICATE_BID_ID")
        ids.add(bid["bid_id"])
        decimal(bid.get("alpha_usd_mt"), f"{bid['bid_id']}.alpha")
    selected = fixture.get("pi_selected_bid", {})
    _required_synthetic(selected, "pi_selected_bid")
    if selected.get("bid_id") is not None and selected["bid_id"] not in ids:
        raise ValueError("UNKNOWN_PI_SELECTED_BID")
