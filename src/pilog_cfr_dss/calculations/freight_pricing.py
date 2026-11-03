"""TCE pricing is net of voyage expenses/commission, BEFORE owned running."""
from decimal import Decimal, ROUND_CEILING
from typing import Iterable


def total_commission(rates: Iterable[Decimal]) -> Decimal:
    rates = tuple(rates)
    if any(not r.is_finite() or r < 0 for r in rates):
        raise ValueError("INVALID_COMMISSION")
    result = sum(rates, Decimal(0))
    if result >= 1:
        raise ValueError("INVALID_COMMISSION_SUM")
    return result


def contribution_delta(contribution: Decimal, baseline: Decimal) -> Decimal:
    return contribution - baseline


def required_freight(voyage_expenses: Decimal, days: Decimal, quantity: Decimal,
                     target_tce: Decimal, commission_fraction: Decimal) -> Decimal:
    values = (voyage_expenses, days, quantity, target_tce, commission_fraction)
    if any(not x.is_finite() for x in values) or min(values) < 0 or days == 0 or quantity == 0 or commission_fraction >= 1:
        raise ValueError("INVALID_TCE_PRICING_INPUT")
    rate = (voyage_expenses + target_tce * days) / (quantity * (1 - commission_fraction))
    return rate.quantize(Decimal("0.0001"), rounding=ROUND_CEILING)


def economics(costs: dict[str, Decimal], rate: Decimal, quantity: Decimal,
              commission_fraction: Decimal) -> dict[str, Decimal]:
    if any(not x.is_finite() for x in (rate, quantity, commission_fraction)) or rate < 0 or quantity <= 0 or not 0 <= commission_fraction < 1:
        raise ValueError("INVALID_ECONOMICS_INPUT")
    revenue = rate * quantity
    commission = revenue * commission_fraction
    net = revenue - commission
    tce = (net - costs["voyage_expenses_usd"]) / costs["total_days"]
    contribution = net - costs["total_cash_cost_usd"]
    return {**costs, "freight_usd_mt": rate, "revenue_usd": revenue, "commission_usd": commission,
            "net_revenue_usd": net, "tce_before_running_usd_day": tce,
            "contribution_usd": contribution, "cost_per_mt_usd": costs["total_cash_cost_usd"] / quantity}


def commercial_financials(quantity: Decimal, bids: list[dict], baseline: dict[str, Decimal]) -> dict:
    """USD amounts for one shipment, not accounting revenue recognition.

    Bid prices are USD/MT; quantity is MT. Existing net_revenue_usd is ONLY
    after commission. net_after_voyage_usd is the existing contribution after
    commission AND all modelled voyage costs. No commodity costs were supplied,
    so PI net is unknown, never zero or FOB minus OE/HPS.
    """
    keys = ("revenue_usd", "total_cash_cost_usd", "commission_usd",
            "net_revenue_usd", "contribution_usd")
    values = [quantity, *(baseline.get(key) for key in keys)]
    if any(not isinstance(v, Decimal) or not v.is_finite() for v in values):
        raise ValueError("INVALID_COMMERCIAL_SUMMARY_INPUT")
    if quantity <= 0 or min(baseline[key] for key in keys[:3]) < 0:
        raise ValueError("INVALID_COMMERCIAL_SUMMARY_RANGE")
    amounts = []
    for bid in bids:
        prices = [bid.get(key) for key in ("fob_usd_mt", "freight_usd_mt", "cfr_usd_mt")]
        if any(not isinstance(v, Decimal) or not v.is_finite() or v < 0 for v in prices):
            raise ValueError("INVALID_COMMERCIAL_BID_PRICE")
        amounts.append({
            "bid_id": bid["bid_id"], "buyer_id": bid["buyer_id"],
            "pi_goods_gross_revenue_usd": prices[0] * quantity,
            "pilog_gross_freight_revenue_usd": prices[1] * quantity,
            "buyer_cfr_offer_value_usd": prices[2] * quantity,
        })
    return {
        "version": "I4-FINANCIALS.1", "quantity_mt": quantity,
        "pi": {"goods_cost_usd": None, "net_result_usd": None, "cost_status": "NOT_MODELLED"},
        "pilog": {
            "gross_revenue_usd": baseline["revenue_usd"],
            "voyage_cost_usd": baseline["total_cash_cost_usd"],
            "commission_usd": baseline["commission_usd"],
            "total_deductions_usd": baseline["total_cash_cost_usd"] + baseline["commission_usd"],
            "revenue_after_commission_usd": baseline["net_revenue_usd"],
            "net_after_voyage_usd": baseline["contribution_usd"],
        },
        "bid_amounts": amounts,
        "recognition": "ESTIMATE_NOT_REALISED_REVENUE",
        "net_scope": "PILOG shipment contribution; not company net profit or full vessel cycle",
    }


def decision_metrics(baseline: dict[str, Decimal], quantity: Decimal,
                     commission_fraction: Decimal, running_usd_day: Decimal,
                     port_do_mt_day: Decimal, do_price_usd_mt: Decimal) -> dict:
    """Derived information only; no new gate, SLA, risk limit or profit claim.

    Port-delay sensitivity holds lump-sum port costs, rate, commission, sea leg
    and fuel prices fixed. Positive delay buffer is additional to baseline.
    """
    cash = baseline.get("total_cash_cost_usd")
    contribution = baseline.get("contribution_usd")
    commission = baseline.get("commission_usd")
    values = (quantity, commission_fraction, running_usd_day, port_do_mt_day,
              do_price_usd_mt, cash, contribution, commission)
    if any(not isinstance(x, Decimal) or not x.is_finite() for x in values):
        raise ValueError("INVALID_DECISION_METRIC_INPUT")
    if quantity <= 0 or not 0 <= commission_fraction < 1 or min(running_usd_day, port_do_mt_day, do_price_usd_mt, cash, commission) < 0:
        raise ValueError("INVALID_DECISION_METRIC_RANGE")
    daily = running_usd_day + port_do_mt_day * do_price_usd_mt
    if contribution < 0:
        buffer, status = None, "BASELINE_ALREADY_NEGATIVE"
    elif daily == 0:
        buffer, status = None, "NO_INCREMENTAL_DAILY_COST_MODELLED"
    elif contribution == 0:
        buffer, status = Decimal(0), "BASELINE_BREAK_EVEN"
    else:
        buffer, status = contribution / daily, "POSITIVE_MODELLED_BUFFER"
    return {
        "contribution_per_mt_usd": contribution / quantity,
        "freight_break_even_usd_mt": cash / (quantity * (1 - commission_fraction)),
        "incremental_port_day_usd": daily,
        "additional_port_days_to_break_even": buffer,
        "delay_buffer_status": status,
        "total_cost_including_commission_usd": cash + commission,
        "is_gate": False,
    }
