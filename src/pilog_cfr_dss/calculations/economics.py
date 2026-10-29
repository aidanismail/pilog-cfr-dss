from __future__ import annotations

from decimal import Decimal


def required_rate_net_of_commission_usd_mt(
    total_cost_usd: Decimal,
    target_net_contribution_usd: Decimal,
    billable_cargo_mt: Decimal,
    total_commission_fraction: Decimal,
) -> Decimal:
    """Rate that reaches target contribution after ad-valorem freight commission."""
    if total_cost_usd < 0 or billable_cargo_mt <= 0 or not Decimal(0) <= total_commission_fraction < Decimal(1):
        raise ValueError("INVALID_NET_REQUIRED_RATE_INPUT")
    return (total_cost_usd + target_net_contribution_usd) / (
        billable_cargo_mt * (Decimal(1) - total_commission_fraction)
    )
