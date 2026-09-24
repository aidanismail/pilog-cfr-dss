from __future__ import annotations

from decimal import Decimal
from typing import Iterable

from pilog_cfr_dss.models.contracts import CostLine


def daily_cost_usd(payable_days: Decimal, rate_usd_day: Decimal) -> Decimal:
    if payable_days < 0 or rate_usd_day < 0:
        raise ValueError("INVALID_DAILY_COST_INPUT")
    return payable_days * rate_usd_day


def total_cost_usd(lines: Iterable[CostLine]) -> Decimal:
    seen: set[str] = set()
    total = Decimal(0)
    for line in lines:
        if line.amount_usd < 0 or not line.mechanisms:
            raise ValueError(f"INVALID_COST_LINE:{line.code}")
        overlap = seen & line.mechanisms
        if overlap:
            raise ValueError(f"DOUBLE_COUNTED_COST:{','.join(sorted(overlap))}")
        seen.update(line.mechanisms)
        total += line.amount_usd
    return total


def commission_usd(gross_revenue_usd: Decimal, rates: Iterable[Decimal]) -> Decimal:
    rates = tuple(rates)
    if gross_revenue_usd < 0 or any(rate < 0 for rate in rates) or sum(rates, Decimal(0)) > 1:
        raise ValueError("INVALID_COMMISSION_INPUT")
    return gross_revenue_usd * sum(rates, Decimal(0))
