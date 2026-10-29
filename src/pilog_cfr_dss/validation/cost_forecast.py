"""Versioned cost estimates bound to an unchanged quote and original voyage rows."""
from dataclasses import replace
from decimal import Decimal
import hashlib
import json

from pilog_cfr_dss.models.iteration_04 import UNITS

FORECAST_VERSION = "COST-FORECAST.1"
REVIEW_VERSION = "I4-COMMERCIAL.1"
COST_KEYS = (
    "port_other_total_usd", "fo_price_usd_mt", "do_price_usd_mt", "waiting_days",
    "loading_rate_mt_day", "discharge_rate_mt_day", "speed_knots", "sea_fo_mt_day",
    "sea_do_mt_day", "port_do_mt_day", "running_usd_day",
)
POSITIVE_KEYS = {"loading_rate_mt_day", "discharge_rate_mt_day", "speed_knots"}


def quote_basis_hash(rows: list | tuple, quote: dict) -> str:
    raw = json.dumps({"rows": list(rows), "quote": quote}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def forecast_values(context: dict, rows: list | tuple, values: dict) -> dict:
    forecast = context.get("cost_forecast")
    result = dict(values)
    if forecast is None:
        return result
    from pilog_cfr_dss.validation.iteration_04 import number, timestamp
    quote = context.get("freight_tender")
    if not isinstance(forecast, dict) or forecast.get("version") != FORECAST_VERSION:
        raise ValueError("INVALID_COST_FORECAST_VERSION")
    if not quote or not quote.get("price_id") or forecast.get("basis_price_id") != quote["price_id"]:
        raise ValueError("COST_FORECAST_QUOTE_MISMATCH")
    if forecast.get("basis_hash") != quote_basis_hash(rows, quote):
        raise ValueError("COST_FORECAST_BASIS_HASH_MISMATCH")
    if not all(isinstance(forecast.get(key), str) and forecast[key].strip() for key in ("forecast_id", "reason", "recorded_at")):
        raise ValueError("MISSING_COST_FORECAST_EVIDENCE")
    timestamp(forecast["recorded_at"])
    overrides = forecast.get("overrides")
    if not isinstance(overrides, dict) or set(overrides) - set(COST_KEYS):
        raise ValueError("UNSUPPORTED_COST_FORECAST_FIELD")
    for key, record in overrides.items():
        if not isinstance(record, dict) or record.get("unit") != UNITS[key] or not record.get("source_status"):
            raise ValueError("INVALID_COST_FORECAST_UNIT_OR_SOURCE:" + key)
        value = number(record.get("value"), key, Decimal(0))
        if key in POSITIVE_KEYS and value <= 0:
            raise ValueError("NONPOSITIVE_COST_FORECAST:" + key)
        result[key] = value
    return result


def effective_case(case):
    return replace(case, values=forecast_values(case.context, case.rows, case.values))
