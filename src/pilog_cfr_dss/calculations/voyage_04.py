"""One-way owned dry-bulk days and cost. Pure functions, no workbook I/O."""
from decimal import Decimal
from pilog_cfr_dss.calculations.voyage_days import sea_days, port_days
from pilog_cfr_dss.calculations.fuel import sea_fuel_mt, fuel_cost_usd
from pilog_cfr_dss.calculations.costs import daily_cost_usd
from pilog_cfr_dss.models.iteration_04 import Case04


def port_expenses_total(components) -> Decimal:
    """Aggregate port/other components once, excluding bunker and running."""
    values = tuple(components)
    if not values or any(not v.is_finite() or v < 0 for v in values):
        raise ValueError("INVALID_PORT_EXPENSE_COMPONENTS")
    return sum(values, Decimal(0))


def voyage(case: Case04, fuel_shock: Decimal = Decimal(0), extra_port_days: Decimal = Decimal(0)) -> dict[str, Decimal]:
    if not fuel_shock.is_finite() or not extra_port_days.is_finite() or min(fuel_shock, extra_port_days) < 0:
        raise ValueError("INVALID_STRESS")
    n = case.number
    sea = sea_days(n("distance_nm"), n("speed_knots"))
    loading = port_days(n("cargo_mt"), n("loading_rate_mt_day"))
    discharge = port_days(n("cargo_mt"), n("discharge_rate_mt_day"))
    port = loading + discharge + n("waiting_days") + extra_port_days
    days = sea + port
    fo_mt = sea_fuel_mt(sea, n("sea_fo_mt_day"))
    sea_do = sea_fuel_mt(sea, n("sea_do_mt_day"))
    port_do = sea_fuel_mt(port, n("port_do_mt_day"))
    fo = fuel_cost_usd(fo_mt, n("fo_price_usd_mt") * (1 + fuel_shock))
    diesel = fuel_cost_usd(sea_do + port_do, n("do_price_usd_mt") * (1 + fuel_shock))
    bunker = fo + diesel
    other = n("port_other_total_usd")
    running = daily_cost_usd(days, n("running_usd_day"))
    return {"sea_days": sea, "loading_days": loading, "discharge_days": discharge,
            "waiting_days": n("waiting_days"), "extra_port_days": extra_port_days,
            "total_days": days, "fo_mt": fo_mt, "sea_do_mt": sea_do, "port_do_mt": port_do,
            "fo_cost_usd": fo, "do_cost_usd": diesel, "bunker_usd": bunker,
            "port_other_usd": other, "running_usd": running,
            "voyage_expenses_usd": bunker + other, "total_cash_cost_usd": bunker + other + running}
