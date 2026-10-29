from __future__ import annotations

from decimal import Decimal


def fob_usd_mt(index_usd_mt: Decimal, alpha_usd_mt: Decimal) -> Decimal:
    return index_usd_mt + alpha_usd_mt


def cfr_usd_mt(fob_price_usd_mt: Decimal, freight_selling_rate_usd_mt: Decimal, adjustment_usd_mt: Decimal) -> Decimal:
    return fob_price_usd_mt + freight_selling_rate_usd_mt + adjustment_usd_mt


def freight_cost_per_mt(total_cost_usd: Decimal, billable_cargo_mt: Decimal) -> Decimal:
    if total_cost_usd < 0 or billable_cargo_mt <= 0:
        raise ValueError("INVALID_COST_PER_MT_INPUT")
    return total_cost_usd / billable_cargo_mt


def required_freight_rate_usd_mt(total_cost_usd: Decimal, target_contribution_usd: Decimal, billable_cargo_mt: Decimal) -> Decimal:
    if total_cost_usd < 0 or billable_cargo_mt <= 0:
        raise ValueError("INVALID_REQUIRED_RATE_INPUT")
    return (total_cost_usd + target_contribution_usd) / billable_cargo_mt


def gross_freight_revenue_usd(rate_usd_mt: Decimal, billable_cargo_mt: Decimal) -> Decimal:
    if rate_usd_mt < 0 or billable_cargo_mt < 0:
        raise ValueError("INVALID_REVENUE_INPUT")
    return rate_usd_mt * billable_cargo_mt


def net_freight_contribution_usd(gross_revenue_usd: Decimal, commission_usd: Decimal, relevant_cost_usd: Decimal) -> Decimal:
    if min(gross_revenue_usd, commission_usd, relevant_cost_usd) < 0:
        raise ValueError("INVALID_CONTRIBUTION_INPUT")
    return gross_revenue_usd - commission_usd - relevant_cost_usd
