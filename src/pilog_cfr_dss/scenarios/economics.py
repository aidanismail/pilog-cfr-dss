from __future__ import annotations

from dataclasses import replace
from decimal import Decimal, InvalidOperation
from typing import Any

from pilog_cfr_dss.calculations.costs import commission_usd, daily_cost_usd, total_cost_usd
from pilog_cfr_dss.calculations.pricing import (
    cfr_usd_mt, freight_cost_per_mt, gross_freight_revenue_usd,
    net_freight_contribution_usd,
)
from pilog_cfr_dss.models.contracts import CaseSnapshot, CostLine, ScenarioEvidence


def _decimal(value: Any, name: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise ValueError(f"MISSING_OR_INVALID:{name}") from error
    if not result.is_finite():
        raise ValueError(f"MISSING_OR_INVALID:{name}")
    return result


def calculate_case_dataset_scenario(
    case: CaseSnapshot,
    scenario: ScenarioEvidence,
    physical: dict[str, Any],
    fob_price_usd_mt: Decimal,
) -> tuple[ScenarioEvidence, dict[str, Any]]:
    if scenario.sales_term != "CFR":
        return scenario, {}
    if scenario.feasible is False:
        return scenario, {"status": "INFEASIBLE", "reasons": list(scenario.reasons)}
    if physical.get("status") != "PARTIAL_PHYSICAL_ESTIMATE":
        reason = "MISSING_PHYSICAL_CALCULATION"
        return replace(scenario, calculation_status="HOLD_DATA_ISSUE", reasons=(*scenario.reasons, reason)), {"status": "HOLD_DATA_ISSUE", "reasons": [reason]}
    definitions = case.manual.get("economic_definitions", {})
    required = {
        "freight_rate_object": "selling_rate",
        "other_voyage_cost_scope": "port_and_other_excluding_bunker_and_daily",
        "daily_cost_day_basis": "total_voyage_days",
        "commission_basis": "gross_revenue_cumulative",
        "decision_objective": "net_freight_contribution_usd",
        "owned_cost_boundary": "running_costs_plus_bunker_plus_other",
    }
    wrong = [name for name, expected in required.items() if definitions.get(name) != expected]
    if wrong:
        reasons = (*scenario.reasons, *(f"UNCONFIRMED_DEFINITION:{name}" for name in wrong))
        return replace(scenario, calculation_status="HOLD_DEFINITION_REQUIRED", reasons=reasons), {
            "status": "HOLD_DEFINITION_REQUIRED", "reasons": list(reasons)
        }
    try:
        cargo = case.number("dwcc_cargo_quantity_mt")
        days = _decimal(physical["results"]["total_voyage_days"]["value"], "total_voyage_days")
        fuel_oil = _decimal(physical["results"]["fuel_oil_sea_cost_usd"]["value"], "fuel_oil_sea_cost_usd")
        diesel = _decimal(physical["results"]["diesel_sea_and_port_cost_usd"]["value"], "diesel_sea_and_port_cost_usd")
        running = daily_cost_usd(days, case.number("running_costs_usd_day"))
        bunker = fuel_oil + diesel
        port_other = case.number("other_voyage_costs_total_usd")
        cost = total_cost_usd((
            CostLine("owned_running", running, frozenset({"owned_running_cost"})),
            CostLine("bunker", bunker, frozenset({"fuel_oil", "diesel"})),
            CostLine("port_and_other", port_other, frozenset({"port", "agency", "other_voyage"})),
        ))
        selling_rate = case.number("freight_rate_usd_mt")
        gross = gross_freight_revenue_usd(selling_rate, cargo)
        rate_items = (
            ("freight_commission", case.number("freight_commission_rate")),
            ("broker_fee", case.number("broker_fee_rate")),
            ("additional_commission", case.number("additional_commission_rate")),
        )
        commission_lines = {name: str(commission_usd(gross, (rate,))) for name, rate in rate_items}
        commission = commission_usd(gross, (rate for _, rate in rate_items))
        contribution = net_freight_contribution_usd(gross, commission, cost)
        adjustment = _decimal(case.manual["pricing"]["cfr_adjustment"]["value"], "cfr_adjustment")
        cfr = cfr_usd_mt(fob_price_usd_mt, selling_rate, adjustment)
        if cfr < 0:
            raise ValueError("INVALID_CFR_PRICE")
        cost_per_mt = freight_cost_per_mt(cost, cargo)
    except (KeyError, ValueError) as error:
        reason = str(error)
        reasons = (*scenario.reasons, reason)
        return replace(scenario, calculation_status="HOLD_DATA_ISSUE", reasons=reasons), {
            "status": "HOLD_DATA_ISSUE", "reasons": list(reasons)
        }
    calculated = replace(
        scenario, comparable=True, contribution_usd=contribution,
        calculation_status="CALCULATED",
        reasons=(*scenario.reasons, "CALCULATED_FROM_DATASET_SIMULATION_BOUNDARY"),
    )
    detail = {
        "status": "CALCULATED",
        "cargo_mt": str(cargo), "total_voyage_days": str(days),
        "owned_running_cost_usd": str(running), "fuel_oil_cost_usd": str(fuel_oil),
        "diesel_cost_usd": str(diesel), "bunker_cost_usd": str(bunker),
        "port_and_other_cost_usd": str(port_other), "total_freight_cost_usd": str(cost),
        "freight_cost_per_mt_usd": str(cost_per_mt),
        "freight_selling_rate_usd_mt": str(selling_rate),
        "gross_freight_revenue_usd": str(gross),
        "commission_components_usd": commission_lines, "commission_usd": str(commission),
        "net_freight_contribution_usd": str(contribution),
        "cfr_adjustment_usd_mt": str(adjustment), "cfr_usd_mt": str(cfr),
        "formulae": {
            "running": "total voyage days * owned running cost USD/day",
            "bunker": "fuel oil cost + diesel oil cost",
            "total_cost": "owned running + bunker + port/other aggregate",
            "revenue": "freight selling rate USD/MT * DWCC cargo MT",
            "commission": "gross freight revenue * sum(three commission fractions)",
            "contribution": "gross freight revenue - commission - total cost",
            "cfr": "FOB + freight selling rate + one explicit adjustment",
        },
    }
    return calculated, detail


def enrich_scenarios(
    case: CaseSnapshot,
    scenarios: tuple[ScenarioEvidence, ...],
    physical: dict[str, Any],
    fob_price_usd_mt: Decimal | None,
) -> tuple[tuple[ScenarioEvidence, ...], dict[str, Any]]:
    enriched: list[ScenarioEvidence] = []
    details: dict[str, Any] = {}
    for scenario in scenarios:
        if scenario.sales_term == "CFR" and fob_price_usd_mt is not None:
            result, detail = calculate_case_dataset_scenario(case, scenario, physical, fob_price_usd_mt)
            enriched.append(result)
            details[scenario.scenario_id] = detail
        else:
            enriched.append(scenario)
    return tuple(enriched), details
