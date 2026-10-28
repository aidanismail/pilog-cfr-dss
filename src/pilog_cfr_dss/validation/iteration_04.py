"""I4 technical checks; mixed source years are notes, not eligibility rules."""
import csv
import json
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from pilog_cfr_dss.models.iteration_04 import Case04, TEXT_KEYS, UNITS, VERSION
from pilog_cfr_dss.calculations.pricing_04 import total_commission


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("DUPLICATE_JSON_KEY:" + key)
        result[key] = value
    return result


def number(value: Any, key: str, minimum: Decimal | None = None) -> Decimal:
    if isinstance(value, (bool, dict, list)) or value is None or str(value).strip() == "":
        raise ValueError(f"INVALID_NUMBER:{key}")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f"INVALID_NUMBER:{key}") from None
    if not result.is_finite() or (minimum is not None and result < minimum):
        raise ValueError(f"INVALID_RANGE:{key}")
    return result


def timestamp(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("INVALID_CASE_TIME")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("INVALID_CASE_TIME") from None
    if result.tzinfo is None:
        raise ValueError("CASE_TIME_REQUIRES_TIMEZONE")
    return result


def record(data: Any, key: str, unit: str) -> Decimal:
    if not isinstance(data, dict) or data.get("unit") != unit:
        raise ValueError(f"INVALID_RECORD_UNIT:{key}")
    if not data.get("source_status"):
        raise ValueError(f"MISSING_SOURCE_LABEL:{key}")
    return number(data.get("value"), key, Decimal(0))


def load_case(path: Path, *, pre_tender: bool = False) -> tuple[Case04, Path]:
    """Load shared voyage inputs; final evaluation remains strict by default.

    Pre-tender preparation does not require commodity prices, bids or scenarios.
    It is not an eligibility decision and cannot produce GO/NO GO.
    """
    context = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object)
    if not isinstance(context, dict) or context.get("schema_version") != VERSION or context.get("mode") != "simulation":
        raise ValueError("INVALID_I4_VERSION_OR_MODE")
    if not isinstance(context.get("case_id"), str) or not context["case_id"].strip():
        raise ValueError("MISSING_CASE_ID")
    name = context.get("voyage_dataset")
    if not isinstance(name, str) or Path(name).name != name or not name.endswith(".csv"):
        raise ValueError("INVALID_DATASET_PATH")
    dataset = path.parent / name
    with dataset.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if any(not isinstance(row, dict) or None in row for row in rows):
        raise ValueError("MALFORMED_CSV")
    keys = [row.get("key") for row in rows]
    if set(keys) != set(UNITS) or len(keys) != len(UNITS):
        raise ValueError("I4_DATASET_KEY_MISMATCH")
    values = {}
    notes = []
    for row in rows:
        key = row["key"]
        if row.get("unit") != UNITS[key]:
            raise ValueError(f"INVALID_UNIT:{key}")
        if not row.get("source_status"):
            raise ValueError(f"MISSING_SOURCE_LABEL:{key}")
        if not row.get("source_reference"):
            notes.append(f"Referensi sumber belum tersedia: {key}.")
        raw = row.get("value")
        if raw is None or not raw.strip():
            raise ValueError(f"MISSING_VALUE:{key}")
        values[key] = raw.strip() if key in TEXT_KEYS else number(raw, key, Decimal(0))
    for key in ("cargo_mt", "dwt_mt", "distance_nm", "speed_knots", "loading_rate_mt_day", "discharge_rate_mt_day"):
        if values[key] <= 0:
            raise ValueError(f"NONPOSITIVE_INPUT:{key}")
    if (values["cargo_category"], values["vessel_mode"], values["voyage_boundary"]) != ("dry_bulk", "owned", "laden_only"):
        raise ValueError("OUTSIDE_I4_SCOPE")
    commissions = [values[k] for k in UNITS if k.endswith("fraction")]
    total_commission(commissions)
    pricing = context.get("pricing")
    if not isinstance(pricing, dict) or pricing.get("basis") != "tce_net_voyage_before_running":
        raise ValueError("UNSUPPORTED_PRICING_BASIS")
    if pricing.get("quote_commission_basis") not in {"net_of_commission", "simulation_assumed_net"}:
        raise ValueError("QUOTE_COMMISSION_BASIS_REQUIRES_NORMALIZATION")
    record(pricing.get("target_tce"), "target_tce", "USD/day")
    if context.get("freight_tender") is not None:
        record(context["freight_tender"], "freight_tender", "USD/MT")
        for event in ("fixed_at", "calculated_at"):
            if context["freight_tender"].get(event) is not None:
                timestamp(context["freight_tender"][event])
    from pilog_cfr_dss.validation.market_sources import validate_market_binding
    validate_market_binding(context, rows, values)
    from pilog_cfr_dss.validation.case_basis import validate_case_basis
    validate_case_basis(context, rows, values)
    from pilog_cfr_dss.validation.cost_forecast import forecast_values
    forecast_values(context, rows, values)
    if pre_tender:
        validate_od(context, values, notes)
        return Case04(values, tuple(rows), context, tuple(notes)), dataset
    observations = context.get("market_index")
    if not isinstance(observations, dict) or set(observations) != {"argus", "fertecon"}:
        raise ValueError("MISSING_INDEX_PUBLISHER")
    dates = set()
    for publisher, obs in observations.items():
        if not isinstance(obs, dict) or obs.get("unit") != "USD/MT" or obs.get("basis") != "FOB SEA granular":
            raise ValueError(f"INDEX_BASIS_MISMATCH:{publisher}")
        if not obs.get("source_status"):
            raise ValueError(f"MISSING_SOURCE_LABEL:{publisher}")
        lo, hi = number(obs.get("low"), publisher), number(obs.get("high"), publisher)
        if lo <= 0 or hi < lo:
            raise ValueError(f"INVALID_INDEX_RANGE:{publisher}")
        dates.add(obs.get("observation_date"))
    if len(dates) != 1 or None in dates or "" in dates:
        notes.append("Tanggal dua laporan indeks berbeda/belum lengkap; diperbolehkan untuk simulasi, bukan harga sinkron terkini.")
    record(context.get("oe_hps"), "oe_hps", "USD/MT")
    validate_od(context, values, notes)
    policy = context.get("vessel_policy")
    if not isinstance(policy, dict) or values["vessel_class"] not in policy:
        raise ValueError("MISSING_VESSEL_CLASS_POLICY")
    bounds = policy[values["vessel_class"]]
    if not isinstance(bounds, list) or len(bounds) != 2 or number(bounds[0], "class min", Decimal(0)) > number(bounds[1], "class max", Decimal(0)):
        raise ValueError("INVALID_CLASS_POLICY")
    cutoff = timestamp(context.get("evaluation_cutoff"))
    clock = context.get("auction_clock")
    if clock is not None:
        from pilog_cfr_dss.models.tender_clock import round_window
        round_window(clock, 1)
    bids = context.get("bids")
    if not isinstance(bids, list) or not bids:
        raise ValueError("MISSING_BIDS")
    ids, slots = set(), set()
    for bid in bids:
        if not isinstance(bid, dict) or not all(isinstance(bid.get(k), str) and bid[k] for k in ("bid_id", "buyer_id", "source_status")):
            raise ValueError("INVALID_BID")
        rd, seq = bid.get("round"), bid.get("sequence")
        if type(rd) is not int or rd < 1 or type(seq) is not int or seq < 1:
            raise ValueError("INVALID_BID_ORDER")
        slot = (bid["buyer_id"], rd, seq)
        if bid["bid_id"] in ids or slot in slots:
            raise ValueError("DUPLICATE_BID_ID_OR_ORDER")
        ids.add(bid["bid_id"]); slots.add(slot)
        if bid.get("status") not in {"active", "withdrawn", "expired", "replaced"}:
            raise ValueError("INVALID_BID_STATUS")
        number(bid.get("alpha_usd_mt"), "alpha")
        if clock is not None and "submitted_at" not in bid:
            raise ValueError("SCHEDULED_BID_REQUIRES_SUBMITTED_AT")
        if "submitted_at" in bid:
            submitted = timestamp(bid["submitted_at"])
            if "valid_until" in bid and timestamp(bid["valid_until"]) < submitted:
                raise ValueError("BID_VALIDITY_BEFORE_SUBMISSION")
        elif "valid_until" in bid:
            timestamp(bid["valid_until"])
    selection = context.get("pi_selected_bid_id")
    if selection is not None and (not isinstance(selection, str) or selection not in ids):
        raise ValueError("UNKNOWN_PI_SELECTED_BID")
    scenarios = context.get("scenarios")
    if not isinstance(scenarios, list):
        raise ValueError("INVALID_SCENARIOS")
    scenario_ids = set()
    for shock in scenarios:
        if not isinstance(shock, dict) or not isinstance(shock.get("scenario_id"), str) or not shock["scenario_id"] or shock["scenario_id"] in scenario_ids or shock["scenario_id"] == "baseline":
            raise ValueError("INVALID_SCENARIO_ID")
        scenario_ids.add(shock["scenario_id"])
        number(shock.get("fuel_price_increase_fraction"), "fuel shock", Decimal(0))
        number(shock.get("extra_port_days"), "port delay", Decimal(0))
        if not shock.get("source_status"):
            raise ValueError("MISSING_SCENARIO_LABEL")
    notes.extend(context.get("limitations", []) if isinstance(context.get("limitations", []), list) else [])
    notes.append("Tahun sumber boleh berbeda; hasil hanya simulasi logika, bukan quotation/harga pasar terkini.")
    return Case04(values, tuple(rows), context, tuple(notes)), dataset


def validate_od(context: dict, values: dict, notes: list) -> None:
    """Informational matching shared by preparation and final evaluation."""
    if context.get("od_usage") == "distance_only":
        return
    od = context.get("od_reference")
    try:
        record(od, "od_reference", "USD/MT")
        if od.get("quote_basis") != "one_way_shipment" or od.get("cost_coverage") != "includes_return":
            raise ValueError("OD_BASIS_NOT_DECLARED")
        if od.get("loading_port") != values["loading_port"] or od.get("discharging_port") != values["discharging_port"]:
            raise ValueError("OD_ROUTE_MISMATCH")
        if number(od.get("cargo_mt"), "od cargo") != values["cargo_mt"] or od.get("vessel_class") != values["vessel_class"]:
            raise ValueError("OD_CASE_BASIS_MISMATCH")
        context["od_reference_valid"] = True
    except (ValueError, TypeError, AttributeError) as error:
        context["od_reference_valid"] = False
        notes.append("OD belum dapat dibandingkan: " + str(error) + "; tidak menjadi veto GO/NO GO.")
