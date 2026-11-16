"""Deterministic cost-based dry-bulk calculator shared by UI, CLI and matrix."""
from decimal import Decimal, ROUND_CEILING, localcontext
from pilog_cfr_dss.calculations.capacity import bulk_capacity
from pilog_cfr_dss.calculations.voyage_days import sea_days
from pilog_cfr_dss.calculations.costs import daily_cost_usd
from pilog_cfr_dss.calculations.fuel import fuel_cost_usd, sea_fuel_mt
from pilog_cfr_dss.calculations.port_time import advance, port_duration
from pilog_cfr_dss.models.freight_desk import COMMODITIES, FORMULA, SCHEMA, terms_catalog
from pilog_cfr_dss.validation.numbers import number, timestamp

ZERO = Decimal(0)


def quantities(cargo, tolerance_percent):
    q, t = number(cargo, "cargo_mt"), number(tolerance_percent, "tolerance_percent")
    if q <= 0 or not 0 <= t < 100:
        raise ValueError("INVALID_CARGO_OR_TOLERANCE")
    return {"minimum": q * (1 - t / 100), "nominal": q, "maximum": q * (1 + t / 100)}


def _activity(name, days, hire_rate, vlsfo_rate, lsmgo_rate, prices, port_da=ZERO, extra=ZERO):
    vlsfo = sea_fuel_mt(days, vlsfo_rate)
    lsmgo = sea_fuel_mt(days, lsmgo_rate)
    hire = daily_cost_usd(days, hire_rate)
    fuel = fuel_cost_usd(vlsfo, prices["VLSFO"]) + fuel_cost_usd(lsmgo, prices["LSMGO"])
    return {"activity": name, "days": days, "hire_rate": hire_rate, "hire_usd": hire,
            "vlsfo_mt": vlsfo, "lsmgo_mt": lsmgo, "bunker_usd": fuel,
            "port_da_usd": port_da, "other_usd": extra,
            "total_usd": hire + fuel + port_da + extra}


def _scenario(case, family, profile, quantity, prices):
    load, discharge = case["ports"]["load"], case["ports"]["discharge"]
    cap = bulk_capacity(profile, quantity, number(case["stowage_factor_m3_mt"], "SF"),
                        [load["draft_limit_m"], discharge["draft_limit_m"]])
    result = {"vessel_class": family, "cargo_mt": quantity, "capacity": cap,
              "feasible": cap["feasible"], "ledger": [], "status": "CAPACITY_FAIL" if not cap["feasible"] else "CALCULATED"}
    if not cap["feasible"]:
        return result
    hire = number(case["hire_usd_day"], "hire_usd_day", ZERO)
    speed = number(profile["speed_knots"], "speed_knots")
    sea = sea_days(number(case["distance_nm"], "distance_nm"), speed)
    cursor = timestamp(case["start_at"])
    port_v = number(profile["port_vlsfo_mt_day"], "port_vlsfo_mt_day", ZERO)
    port_m = number(profile["port_lsmgo_mt_day"], "port_lsmgo_mt_day", ZERO)
    ledger = []
    dates = {}
    for side, port in (("load", load), ("discharge", discharge)):
        waiting = number(port["waiting_days"], side + "_waiting_days", ZERO)
        cursor = advance(cursor, waiting)
        dates[side + "_start"] = cursor.isoformat()
        elapsed, end = port_duration(quantity, port, cursor)
        allowance = number(port["allowance_days"], side + "_allowance_days", ZERO)
        dates[side + "_end"] = advance(end, allowance).isoformat()
        cursor = advance(end, allowance)
        if waiting:
            ledger.append(_activity("Tunggu " + side, waiting, hire, port_v, port_m, prices))
        ledger.append(_activity("Muat" if side == "load" else "Bongkar", elapsed + allowance,
                                hire, port_v, port_m, prices, number(port["port_da_usd"], side + "_DA", ZERO)))
        if side == "load":
            cursor = advance(cursor, sea)
            ledger.append(_activity("Laut bermuatan", sea, hire,
                         number(profile["sea_vlsfo_mt_day"], "sea_vlsfo_mt_day", ZERO),
                         number(profile["sea_lsmgo_mt_day"], "sea_lsmgo_mt_day", ZERO), prices))
    delay = number(case["bunker_delay_days"], "bunker_delay_days", ZERO)
    if delay:
        ledger.append(_activity("Bunker delay", delay, hire, port_v, port_m, prices))
    extra = ZERO
    cost_ids = set()
    for item in case["other_costs"]:
        if not item.get("id") or item["id"] in cost_ids or item.get("unit") != "USD":
            raise ValueError("INVALID_OR_DUPLICATE_OTHER_COST")
        cost_ids.add(item["id"])
        extra += number(item["amount"], item["id"], ZERO)
    if extra:
        ledger.append(_activity("Biaya lain", ZERO, hire, ZERO, ZERO, prices, extra=extra))
    days = sum((x["days"] for x in ledger), ZERO)
    hire_total = sum((x["hire_usd"] for x in ledger), ZERO)
    expenses = sum((x["bunker_usd"] + x["port_da_usd"] + x["other_usd"] for x in ledger), ZERO)
    total = expenses + hire_total
    freight = total / quantity
    minimum = freight.quantize(Decimal(".01"), rounding=ROUND_CEILING)
    quoted = case.get("selling_freight_usd_mt")
    commercial = None
    if quoted is not None:
        rate = number(quoted, "selling_freight_usd_mt", ZERO)
        revenue = rate * quantity  # commission fixed at 0% by approved policy
        surplus = revenue - total
        commercial = {"selling_freight_usd_mt": rate, "net_freight_revenue_usd": revenue,
                      "surplus_usd": surplus, "tce_usd_day": (revenue - expenses) / days,
                      "rate_change_to_break_even": max(ZERO, minimum - rate),
                      "shortfall_usd": max(ZERO, -surplus)}
    result.update(ledger=ledger, days=days, sea_days=sea, hire_usd=hire_total,
                  voyage_expenses_usd=expenses, total_usd=total, freight_usd_mt=freight,
                  minimum_offer_usd_mt=minimum, commercial=commercial, timeline=dates,
                  bunker_usd=sum((x["bunker_usd"] for x in ledger), ZERO),
                  port_da_usd=sum((x["port_da_usd"] for x in ledger), ZERO),
                  other_usd=extra)
    return result


def calculate(case):
    if (not isinstance(case, dict) or not isinstance(case.get("ports"), dict)
            or set(case["ports"]) != {"load", "discharge"}
            or not all(isinstance(port, dict) for port in case["ports"].values())
            or not isinstance(case.get("profiles"), dict) or not isinstance(case.get("fuel"), dict)
            or not isinstance(case.get("other_costs"), list)):
        raise ValueError("INVALID_CASE_STRUCTURE")
    if case.get("schema") != SCHEMA:
        raise ValueError("UNSUPPORTED_CASE_VERSION_USE_NEW_FREIGHT_CASE")
    import json
    expected_terms = terms_catalog(case.get("terms_version"))
    if (case.get("formula_version") != FORMULA
            or case.get("terms_snapshot") != json.loads(json.dumps(expected_terms))):
        raise ValueError("FORMULA_OR_TERMS_VERSION_MISMATCH")
    if case.get("currency") != "USD" or case.get("sf_unit") != "m3/MT":
        raise ValueError("INCOMPATIBLE_CASE_UNITS")
    if case.get("commodity") not in COMMODITIES or set(case["profiles"]) != {"Handysize", "Supramax"}:
        raise ValueError("UNSUPPORTED_COMMODITY_OR_CLASS")
    if case.get("commission_fraction") != "0":
        raise ValueError("COMMISSION_MUST_BE_ZERO")
    if number(case["distance_nm"], "distance_nm") <= 0:
        raise ValueError("INVALID_DISTANCE")
    if not case["ports"]["load"]["name"] or not case["ports"]["discharge"]["name"]:
        raise ValueError("PORT_REQUIRED")
    if (case["ports"]["load"]["name"], case["ports"]["load"]["country"]) == (
            case["ports"]["discharge"]["name"], case["ports"]["discharge"]["country"]):
        raise ValueError("SAME_PORT")
    timestamp(case["start_at"])
    for port in case["ports"].values():
        if not isinstance(port.get("name"), str) or not isinstance(port.get("country"), str):
            raise ValueError("INVALID_PORT_STRUCTURE")
        if port["terms"] not in expected_terms or number(port["rate_mt_day"], "handling_rate") <= 0:
            raise ValueError("INVALID_PORT_TERMS_OR_RATE")
    if case.get("selling_freight_usd_mt") is not None:
        number(case["selling_freight_usd_mt"], "selling_freight_usd_mt", ZERO)
    with localcontext() as context:
        context.prec = 40
        qs = quantities(case["cargo_mt"], case["tolerance_percent"])
        prices = {key: number(case["fuel"][key]["value"], key, ZERO) for key in ("VLSFO", "LSMGO")}
        results = {}
        for family, profile in case["profiles"].items():
            results[family] = {}
            for label, quantity in qs.items():
                try:
                    results[family][label] = _scenario(case, family, profile, quantity, prices)
                except (ValueError, KeyError, TypeError) as error:
                    results[family][label] = {"vessel_class": family, "cargo_mt": quantity,
                        "feasible": False, "status": "INPUT_ERROR", "error": str(error), "ledger": []}
        return {"formula_version": FORMULA, "quantities": qs, "classes": results}


def freight_delta(value, base):
    return number(value) - number(base)
