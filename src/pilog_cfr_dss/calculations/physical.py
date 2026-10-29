from __future__ import annotations

from decimal import Decimal
from typing import Any

from pilog_cfr_dss.calculations.fuel import fuel_cost_usd, port_diesel_mt, sea_fuel_mt
from pilog_cfr_dss.calculations.voyage_days import port_days, sea_days, total_days
from pilog_cfr_dss.models.contracts import CaseSnapshot, FORMULA_VERSION


def calculate_physical(case: CaseSnapshot) -> dict[str, Any]:
    q = case.number("dwcc_cargo_quantity_mt")
    laden_days = sea_days(case.number("laden_distance_nm"), case.number("laden_speed_knots"))
    ballast_days = sea_days(case.number("ballast_distance_nm"), case.number("ballast_speed_knots"))
    loading_days = port_days(q, case.number("loading_rate_mt_day"))
    discharge_days = port_days(q, case.number("discharge_rate_mt_day"))
    canal_days = case.number("canal_transit_days")
    voyage_days = total_days(laden_days, ballast_days, loading_days, discharge_days, canal_days)
    fo_laden = sea_fuel_mt(laden_days, case.number("fuel_oil_consumption_laden_mt_day"))
    fo_ballast = sea_fuel_mt(ballast_days, case.number("fuel_oil_consumption_ballast_mt_day"))
    do_laden = sea_fuel_mt(laden_days, case.number("diesel_consumption_at_sea_laden_mt_day"))
    do_ballast = sea_fuel_mt(ballast_days, case.number("diesel_consumption_at_sea_ballast_mt_day"))
    do_port = port_diesel_mt(
        loading_days + discharge_days,
        case.number("auxiliary_engine_power_kw"),
        case.number("in_port_working_load_factor"),
        case.number("in_port_diesel_factor_kg_kwh"),
    )
    fo_cost = fuel_cost_usd(fo_laden + fo_ballast, case.number("fuel_oil_price_usd_mt"))
    do_cost = fuel_cost_usd(do_laden + do_ballast + do_port, case.number("diesel_oil_price_usd_mt"))
    values: dict[str, tuple[Decimal, str, str, list[str]]] = {
        "laden_sea_days": (laden_days, "day", "distance_nm / (speed_knots * 24)", ["laden_distance_nm", "laden_speed_knots"]),
        "ballast_sea_days": (ballast_days, "day", "distance_nm / (speed_knots * 24)", ["ballast_distance_nm", "ballast_speed_knots"]),
        "loading_days": (loading_days, "day", "cargo_mt / loading_rate_mt_day", ["dwcc_cargo_quantity_mt", "loading_rate_mt_day"]),
        "discharge_days": (discharge_days, "day", "cargo_mt / discharge_rate_mt_day", ["dwcc_cargo_quantity_mt", "discharge_rate_mt_day"]),
        "canal_days": (canal_days, "day", "dataset input", ["canal_transit_days"]),
        "total_voyage_days": (voyage_days, "day", "sum(laden sea, ballast sea, loading, discharge, canal)", ["laden_sea_days", "ballast_sea_days", "loading_days", "discharge_days", "canal_days"]),
        "fuel_oil_laden_mt": (fo_laden, "MT", "laden_sea_days * fuel_oil_consumption_laden_mt_day", ["laden_sea_days", "fuel_oil_consumption_laden_mt_day"]),
        "fuel_oil_ballast_mt": (fo_ballast, "MT", "ballast_sea_days * fuel_oil_consumption_ballast_mt_day", ["ballast_sea_days", "fuel_oil_consumption_ballast_mt_day"]),
        "diesel_laden_sea_mt": (do_laden, "MT", "laden_sea_days * diesel_consumption_at_sea_laden_mt_day", ["laden_sea_days", "diesel_consumption_at_sea_laden_mt_day"]),
        "diesel_ballast_sea_mt": (do_ballast, "MT", "ballast_sea_days * diesel_consumption_at_sea_ballast_mt_day", ["ballast_sea_days", "diesel_consumption_at_sea_ballast_mt_day"]),
        "diesel_port_mt": (do_port, "MT", "port_days * 24 * power_kw * load_factor * kg_kwh / 1000", ["loading_days", "discharge_days", "auxiliary_engine_power_kw", "in_port_working_load_factor", "in_port_diesel_factor_kg_kwh"]),
        "fuel_oil_sea_cost_usd": (fo_cost, "USD", "(fuel_oil_laden_mt + fuel_oil_ballast_mt) * fuel_oil_price_usd_mt", ["fuel_oil_laden_mt", "fuel_oil_ballast_mt", "fuel_oil_price_usd_mt"]),
        "diesel_sea_and_port_cost_usd": (do_cost, "USD", "(diesel_laden_sea_mt + diesel_ballast_sea_mt + diesel_port_mt) * diesel_oil_price_usd_mt", ["diesel_laden_sea_mt", "diesel_ballast_sea_mt", "diesel_port_mt", "diesel_oil_price_usd_mt"]),
    }
    return {
        "status": "PARTIAL_PHYSICAL_ESTIMATE",
        "formula_version": FORMULA_VERSION,
        "results": {key: {"value": str(value), "unit": unit, "formula": formula, "inputs": inputs} for key, (value, unit, formula, inputs) in values.items()},
        "limitations": [
            "Port diesel follows the dataset factor; confirm engine and port-operation basis.",
            "Fuel oil at loading/discharging port is excluded until its stock-versus-consumption meaning is confirmed.",
            "Vessel choice uses a separate gross-DWT-only screen; bunker/constants allowance, draft, stowage, terminal constraints, and actual availability are not proven.",
            "No hire, running cost, port tariff, aggregate other cost, or commission is added to this physical estimate.",
        ],
    }
