from __future__ import annotations

from decimal import Decimal


def sea_days(distance_nm: Decimal, speed_knots: Decimal) -> Decimal:
    if distance_nm < 0 or speed_knots <= 0:
        raise ValueError("INVALID_DISTANCE_OR_SPEED")
    return distance_nm / (speed_knots * Decimal(24))


def port_days(cargo_mt: Decimal, handling_rate_mt_day: Decimal) -> Decimal:
    if cargo_mt < 0 or handling_rate_mt_day <= 0:
        raise ValueError("INVALID_CARGO_OR_HANDLING_RATE")
    return cargo_mt / handling_rate_mt_day


def total_days(*segments: Decimal) -> Decimal:
    if not segments or any(segment < 0 for segment in segments):
        raise ValueError("INVALID_VOYAGE_SEGMENT")
    return sum(segments, Decimal(0))
