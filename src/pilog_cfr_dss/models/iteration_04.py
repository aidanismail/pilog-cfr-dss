"""Versioned I4 contracts; no I3 assumptions or calculation side effects."""
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

VERSION = "I4.1"
REPORT_VERSION = "I4-BRIEF.4"
MARKET_REPORT_VERSION = "I4-BRIEF.5"
CLEAN_REPORT_VERSION = "I4-BRIEF.6"
COMMERCIAL_REPORT_VERSION = "I4-BRIEF.8"
METRICS_VERSION = "I4-METRICS.1"
TEXT_KEYS = {
    "cargo_description", "cargo_category", "loading_port", "discharging_port",
    "vessel_class", "vessel_mode", "voyage_boundary",
}
UNITS = {
    **{key: "text" for key in TEXT_KEYS},
    "cargo_mt": "MT", "dwt_mt": "MT", "bunkers_allowance_mt": "MT",
    "constants_allowance_mt": "MT", "distance_nm": "NM", "speed_knots": "knot",
    "sea_fo_mt_day": "MT/day", "sea_do_mt_day": "MT/day", "port_do_mt_day": "MT/day",
    "loading_rate_mt_day": "MT/day", "discharge_rate_mt_day": "MT/day",
    "waiting_days": "day", "fo_price_usd_mt": "USD/MT", "do_price_usd_mt": "USD/MT",
    "running_usd_day": "USD/day", "port_other_total_usd": "USD",
    "freight_commission_fraction": "fraction", "broker_fraction": "fraction",
    "additional_commission_fraction": "fraction",
}


@dataclass(frozen=True)
class Case04:
    values: dict[str, Decimal | str]
    rows: tuple[dict[str, str], ...]
    context: dict[str, Any]
    notes: tuple[str, ...]

    def number(self, key: str) -> Decimal:
        value = self.values[key]
        if not isinstance(value, Decimal):
            raise ValueError(f"NOT_NUMERIC:{key}")
        return value
