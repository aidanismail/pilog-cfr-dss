from __future__ import annotations

from decimal import Decimal


def sea_fuel_mt(days: Decimal, consumption_mt_day: Decimal) -> Decimal:
    if days < 0 or consumption_mt_day < 0:
        raise ValueError("INVALID_FUEL_INPUT")
    return days * consumption_mt_day


def port_diesel_mt(port_days: Decimal, power_kw: Decimal, load_factor: Decimal, kg_kwh: Decimal) -> Decimal:
    if port_days < 0 or power_kw < 0 or not Decimal(0) <= load_factor <= Decimal(1) or kg_kwh < 0:
        raise ValueError("INVALID_PORT_DIESEL_INPUT")
    return port_days * Decimal(24) * power_kw * load_factor * kg_kwh / Decimal(1000)


def fuel_cost_usd(quantity_mt: Decimal, price_usd_mt: Decimal) -> Decimal:
    if quantity_mt < 0 or price_usd_mt < 0:
        raise ValueError("INVALID_FUEL_COST_INPUT")
    return quantity_mt * price_usd_mt
