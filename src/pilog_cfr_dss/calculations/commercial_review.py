"""Commercial diagnostics; informative metrics, never new eligibility thresholds."""
from decimal import Decimal, ROUND_CEILING


def _valid(*values):
    if any(not isinstance(value, Decimal) or not value.is_finite() for value in values):
        raise ValueError("INVALID_COMMERCIAL_REVIEW_NUMBER")


def net_daily(economics: dict) -> Decimal:
    _valid(economics["contribution_usd"], economics["total_days"])
    if economics["total_days"] <= 0:
        raise ValueError("NONPOSITIVE_REVIEW_DAYS")
    return economics["contribution_usd"] / economics["total_days"]

def demo_port_cost(original: Decimal, contribution: Decimal) -> Decimal:
    """Synthetic fixture only: default 450k, sufficient for loss on any selected profile."""
    _valid(original, contribution)
    if original < 0:
        raise ValueError("INVALID_DEMO_PORT_COST")
    return max(Decimal("450000"), original + max(contribution, Decimal(0)) + Decimal("10000"))


def commercial_review(current: dict, quoted: dict, quantity: Decimal, commission: Decimal,
                      target: Decimal, break_even: Decimal) -> dict:
    _valid(quantity, commission, target, break_even)
    if quantity <= 0 or not 0 <= commission < 1 or target < 0 or break_even < 0:
        raise ValueError("INVALID_COMMERCIAL_REVIEW_RANGE")
    keys = ("bunker_usd", "port_other_usd", "running_usd", "total_cash_cost_usd", "contribution_usd", "tce_before_running_usd_day", "freight_usd_mt")
    _valid(*(row[key] for row in (current, quoted) for key in keys))
    loss = max(-current["contribution_usd"], Decimal(0))
    rounded_break_even = break_even.quantize(Decimal("0.0001"), rounding=ROUND_CEILING)
    drivers = [{"component": key, "at_quote_usd": quoted[key], "current_usd": current[key],
                "change_usd": current[key] - quoted[key]} for key in ("bunker_usd", "port_other_usd", "running_usd")]
    return {"version": "COMMERCIAL-REVIEW.1", "scope": "ECONOMIC_REVIEW_NOT_EXECUTION_APPROVAL",
            "market_acceptance": "NOT_RECORDED", "current_contribution_per_day_usd": net_daily(current),
            "at_quote_contribution_usd": quoted["contribution_usd"],
            "current_contribution_usd": current["contribution_usd"],
            "contribution_change_usd": current["contribution_usd"] - quoted["contribution_usd"],
            "cost_increase_usd": current["total_cash_cost_usd"] - quoted["total_cash_cost_usd"],
            "loss_to_recover_usd": loss, "cost_reduction_to_break_even_usd": loss,
            "minimum_cost_reduction_usd": loss.quantize(Decimal("0.01"), rounding=ROUND_CEILING),
            "break_even_offer_usd_mt": rounded_break_even,
            "hypothetical_freight_increase_usd_mt": max(rounded_break_even - current["freight_usd_mt"], Decimal(0)),
            "actual_tce_usd_day": current["tce_before_running_usd_day"], "target_tce_usd_day": target,
            "tce_gap_usd_day": current["tce_before_running_usd_day"] - target,
            "drivers": drivers, "is_new_gate": False, "automatic_repricing": False}
