"""Pure Decimal calculations for I3 market observations, tender bids and voyage economics."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from pilog_cfr_dss.calculations.capacity import deadweight_headroom_mt
from pilog_cfr_dss.calculations.costs import commission_usd, daily_cost_usd, total_cost_usd
from pilog_cfr_dss.calculations.physical import calculate_physical
from pilog_cfr_dss.calculations.pricing import (
    fob_usd_mt, freight_cost_per_mt, gross_freight_revenue_usd, net_freight_contribution_usd,
)
from pilog_cfr_dss.models.contracts import CaseSnapshot, CostLine
from pilog_cfr_dss.validation.iteration_03 import decimal


def midpoint(low: Decimal, high: Decimal) -> Decimal:
    if low <= 0 or high < low:
        raise ValueError("INVALID_MARKET_RANGE")
    return (low + high) / Decimal(2)


def average_two_publishers(argus: Decimal, fertecon: Decimal) -> Decimal:
    if argus <= 0 or fertecon <= 0:
        raise ValueError("INVALID_MARKET_INDEX")
    return (argus + fertecon) / Decimal(2)


def market_index(fixture: dict[str, Any]) -> tuple[Decimal, dict[str, Any]]:
    observations = fixture["market_index"]
    prices = {}
    for publisher in ("argus", "fertecon"):
        observation = observations[publisher]
        prices[publisher] = midpoint(
            decimal(observation["low"], f"{publisher}.low"),
            decimal(observation["high"], f"{publisher}.high"),
        )
    index = average_two_publishers(prices["argus"], prices["fertecon"])
    return index, {
        "argus_midpoint_usd_mt": str(prices["argus"]),
        "fertecon_midpoint_usd_mt": str(prices["fertecon"]),
        "index_usd_mt": str(index),
        "formula": "I = ((Argus_low + Argus_high) / 2 + (Fertecon_low + Fertecon_high) / 2) / 2",
        "source_status": "simulation_only_synthetic",
        "warning": "Angka fixture bukan harga Argus/Fertecon yang diekstrak dari laporan.",
    }


def tender_bids(index: Decimal, oe_hps: Decimal, bids: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if oe_hps <= 0:
        raise ValueError("INVALID_OE_HPS")
    result = []
    for bid in bids:
        alpha = decimal(bid["alpha_usd_mt"], f"{bid['bid_id']}.alpha")
        fob = fob_usd_mt(index, alpha)
        if fob < 0:
            raise ValueError(f"NEGATIVE_FOB:{bid['bid_id']}")
        gap = fob - oe_hps
        result.append({
            "bid_id": bid["bid_id"], "round": bid["round"], "buyer_id": bid["buyer_id"],
            "alpha_usd_mt": str(alpha), "fob_usd_mt": str(fob),
            "oe_gap_usd_mt": str(gap), "eligible_oe_floor": gap >= 0,
            "source_status": bid["source_status"],
        })
    return result


def owned_voyage_economics(case: CaseSnapshot) -> tuple[dict[str, Any], dict[str, Any]]:
    """OD proxy is total owned voyage cost/Q, not an official OD matrix rate."""
    physical = calculate_physical(case)
    p = physical["results"]
    number = lambda key: decimal(p[key]["value"], key)
    q = case.number("dwcc_cargo_quantity_mt")
    running = daily_cost_usd(number("total_voyage_days"), case.number("running_costs_usd_day"))
    fuel_oil = number("fuel_oil_sea_cost_usd")
    diesel = number("diesel_sea_and_port_cost_usd")
    bunker = fuel_oil + diesel
    other = case.number("other_voyage_costs_total_usd")
    cost = total_cost_usd((
        CostLine("owned_running", running, frozenset({"owned_running"})),
        CostLine("bunker", bunker, frozenset({"fuel_oil", "diesel"})),
        CostLine("port_and_other", other, frozenset({"port_and_other"})),
    ))
    od_proxy = freight_cost_per_mt(cost, q)
    selling_rate = case.number("freight_rate_usd_mt")
    revenue = gross_freight_revenue_usd(selling_rate, q)
    rates = (case.number("freight_commission_rate"), case.number("broker_fee_rate"), case.number("additional_commission_rate"))
    commission = commission_usd(revenue, rates)
    contribution = net_freight_contribution_usd(revenue, commission, cost)
    headroom = deadweight_headroom_mt(
        case.number("dwt_mt"), case.number("bunkers_allowance_mt"),
        case.number("constants_allowance_mt"), q,
    )
    economics = {
        "cargo_mt": str(q), "total_voyage_days": str(number("total_voyage_days")),
        "owned_running_usd": str(running), "fuel_oil_usd": str(fuel_oil), "diesel_usd": str(diesel),
        "bunker_usd": str(bunker), "port_and_other_usd": str(other),
        "total_voyage_cost_usd": str(cost), "derived_od_cost_proxy_usd_mt": str(od_proxy),
        "freight_selling_rate_pilog_usd_mt": str(selling_rate),
        "pilog_freight_revenue_usd": str(revenue), "commission_usd": str(commission),
        "pilog_freight_contribution_usd": str(contribution),
        "dwt_headroom_after_allowances_mt": str(headroom),
        "od_source_status": "derived_from_inherited_experimental_data_not_official_matrix",
        "commission_basis_status": "simulation_only_assumption",
        "formulae": {
            "voyage_cost": "owned running + fuel oil + diesel + port/other; hire excluded",
            "od_proxy": "total voyage cost / 45000 MT",
            "freight_revenue": "PILOG freight selling rate * 45000 MT",
            "commission": "freight revenue * sum(three commission fractions)",
            "pilog_contribution": "freight revenue - commission - voyage cost",
        },
    }
    return economics, physical
