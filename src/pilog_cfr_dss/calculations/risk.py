"""Re-run independent stress scenarios against the frozen voyage calculation."""
from copy import deepcopy
from decimal import Decimal, localcontext

from pilog_cfr_dss.calculations.freight_desk import calculate
from pilog_cfr_dss.decisions.risk import fixed_share, risk_rows
from pilog_cfr_dss.models.freight_desk import FORMULA
from pilog_cfr_dss.validation.numbers import number

ZERO, FULL = Decimal(0), Decimal(1)


def price_contract_share(risk, family, key):
    if not risk["scope_matches"]:
        return None
    if key == "hire":
        return fixed_share(risk["commitments"]["charter"]) if risk["charter_class"] == family else None
    if key in ("selling_freight", "physical_freight"):
        return fixed_share(risk["commitments"]["freight"])
    if key in ("VLSFO", "LSMGO") and risk[key]["evidence"] and risk[key]["payer"] != "unknown":
        return fixed_share(risk[key])
    return None


def scenarios_for_class(case, risk, row, exposures):
    family = row["vessel_class"]
    quantity = row["cargo_mt"]
    for key, change in risk["stresses"].items():
        if change is None:
            continue
        if not row["feasible"] and key not in ("cargo", "draft", "physical_freight"):
            continue
        exposure = exposures.get(key, {})
        fixed = price_contract_share(risk, family, key)
        open_share = exposure.get("open_share")
        share = FULL - fixed if fixed is not None else FULL
        conditional = fixed is None or open_share is None or (open_share == 0 and fixed != FULL)
        if open_share and key in ("hire", "selling_freight"):
            share = open_share
        if key == "physical_freight" and open_share is not None:
            share = open_share
        outcome = {"driver": key, "change": change, "scope_share": share if not conditional else None,
                   "owner": exposure.get("owner"), "basis": "Sensitivitas perencanaan" if conditional else "Porsi kontrak tercatat"}
        if key == "physical_freight":
            impact = change * quantity * share
            outcome.update(delta_usd=impact, delta_usd_mt=impact / quantity, exposed_cargo_mt=quantity * share,
                           metric="Biaya freight PI", basis="Sensitivitas perencanaan" if conditional else outcome["basis"])
            yield outcome
            continue

        derived = deepcopy(case)
        if key == "hire":
            item = derived["profiles"][family] if derived["formula_version"] == FORMULA else derived
            item["hire_usd_day"] = row["hire_rate_usd_day"] + change * share
        elif key == "selling_freight":
            commercial = row.get("commercial")
            if commercial is None:
                yield {**outcome, "status": "Isi perkiraan tarif jual untuk menguji penurunan pendapatan."}
                continue
            derived["selling_freight_usd_mt"] = commercial["selling_freight_usd_mt"] + change * share
            if derived["selling_freight_usd_mt"] < 0:
                yield {**outcome, "status": "Tarif jual pada skenario di bawah nol."}
                continue
        elif key in ("VLSFO", "LSMGO"):
            fuel = derived["fuel"][key]
            fuel["value"] = number(fuel["value"]) + change * share
            if fuel["value"] < 0:
                yield {**outcome, "status": f"Harga {key} pada skenario di bawah nol."}
                continue
        elif key in ("load_wait", "discharge_wait"):
            port = derived["ports"]["load" if key == "load_wait" else "discharge"]
            port["waiting_days"] = number(port["waiting_days"]) + change
        elif key == "cargo":
            derived["cargo_mt"] = change
        elif key == "draft":
            derived["ports"]["discharge"]["draft_limit_m"] = change

        if key == "hire" and item["hire_usd_day"] <= 0:
            yield {**outcome, "status": "Hire pada skenario harus lebih dari nol."}
            continue
        checked = calculate(derived)["classes"][family]["nominal"]
        if not checked["feasible"]:
            status = "Input skenario perlu diperiksa" if checked.get("error") else "Skenario tidak lolos kapasitas"
            yield {**outcome, "status": status, "limit_mt": checked.get("capacity", {}).get("limit_mt")}
            continue
        outcome.update(metric="Biaya voyage", total_usd=checked["total_usd"], days=checked["days"],
                       minimum_offer_usd_mt=checked["minimum_offer_usd_mt"],
                       capacity_limit_mt=checked["capacity"]["limit_mt"])
        if row["feasible"]:
            outcome.update(delta_days=checked["days"] - row["days"],
                           delta_usd=checked["total_usd"] - row["total_usd"],
                           delta_usd_mt=checked["freight_usd_mt"] - row["freight_usd_mt"],
                           baseline_usd=row["total_usd"], baseline_usd_mt=row["freight_usd_mt"])
        if key == "hire":
            outcome.update(baseline_rate=row["hire_rate_usd_day"], stressed_rate=checked["hire_rate_usd_day"])
        if key == "selling_freight":
            revenue = checked["commercial"]["net_freight_revenue_usd"]
            impact = revenue - row["commercial"]["net_freight_revenue_usd"]
            outcome.update(metric="Pendapatan freight PILOG", delta_usd=impact, delta_usd_mt=impact / quantity,
                           baseline_usd=row["commercial"]["net_freight_revenue_usd"], total_usd=revenue)
        if checked["commercial"] and key not in ("cargo", "draft") and exposure.get("owner") not in ("PI", "other"):
            commercial = checked["commercial"]
            outcome.update(surplus_usd=commercial["surplus_usd"], tce_usd_day=commercial["tce_usd_day"],
                           margin_basis="Basis kontrak tercatat" if key == "hire" and not conditional and exposure.get("margin_matches")
                           else "Estimasi pada tarif jual input")
        yield outcome


def assess(case, result, risk):
    if risk is None:
        return None
    with localcontext() as context:
        context.prec = 40
        classes = {}
        for family, rows in result["classes"].items():
            row = rows["nominal"]
            cutoff = (row.get("commercial") or {}).get("tce_usd_day")
            exposures = risk_rows(risk, row, rows["maximum"], cutoff)
            stresses = list(scenarios_for_class(case, risk, row, exposures))
            quote_above_limit = exposures["hire"].get("quote_gap_usd_day", ZERO) > 0
            stressed_deficit = any(x.get("surplus_usd", ZERO) < 0 and x.get("margin_basis") == "Basis kontrak tercatat" for x in stresses)
            if quote_above_limit or stressed_deficit:
                exposures["hire"]["priority"] = 1
                exposures["hire"]["action"] = "Tahan penguncian biaya kapal; minta quotation sewa pada atau di bawah hire impas."
            classes[family] = {"exposures": exposures, "scenarios": stresses}

    charter_class = risk["charter_class"]
    selected = result["recommendation"]["selected"] or list(classes)
    if risk["scope_matches"] and charter_class and risk["commitments"]["charter"]["status"] in ("open", "binding"):
        selected = list(dict.fromkeys([charter_class, *selected]))
    relevant = [(line["priority"], key, family, line) for family in selected
                for key, line in classes[family]["exposures"].items() if line["open_share"] != 0]
    confirmed = [item for item in relevant if item[3]["open_share"] is not None or item[0] == 0]
    primary = min(confirmed or relevant, key=lambda x: x[0]) if relevant else None
    action = {**primary[3], "driver": primary[1], "vessel_class": primary[2]} if primary else None
    claims = risk["demurrage"]
    claim_values_entered = any(claims[key] is not None for key in ("payable_usd", "recoverable_usd"))
    if not (risk["scope_matches"] and claims["evidence"] and claims["basis"] and risk["port_delay"]["evidence"]
            and risk["port_delay"]["payer"] != "unknown"):
        claims = {"payable_usd": None, "recoverable_usd": None}
    return {"version": risk["version"], "scope_matches": risk["scope_matches"], "classes": classes,
            "primary": action, "demurrage": claims, "demurrage_entered": claim_values_entered}
