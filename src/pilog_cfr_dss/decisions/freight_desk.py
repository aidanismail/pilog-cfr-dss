"""Prescriptive option selection; no arithmetic, awards or invented thresholds."""
def recommend(result):
    nominal = [rows["nominal"] for rows in result["classes"].values()]
    feasible = [row for row in nominal if row["feasible"]]
    incomplete = [row["vessel_class"] for row in nominal if row["status"] == "INPUT_ERROR"]
    if not feasible:
        if incomplete:
            return {"action": "Lengkapi input kapal sebelum menentukan opsi.",
                    "status": "REVISE", "selected": [], "reasons": ["VESSEL_INPUT_INCOMPLETE"]}
        return {"action": "Ubah muatan atau profil kapal sebelum melanjutkan.",
                "status": "REVISE", "selected": [], "reasons": ["NO_FEASIBLE_NOMINAL_OPTION"]}
    profitable = [row for row in feasible if row["commercial"] is not None and row["commercial"]["surplus_usd"] >= 0]
    eligible = profitable or feasible
    lowest = min(row["freight_usd_mt"] for row in eligible)
    winners = [row for row in eligible if row["freight_usd_mt"] == lowest]
    names = [row["vessel_class"] for row in winners]
    quote = winners[0]["commercial"]
    negative = quote is not None and quote["surplus_usd"] < 0
    limited = any(not result["classes"][name]["maximum"]["feasible"] for name in names)
    action = ("Naikkan tarif jual atau ubah biaya/operasi sebelum menawarkan." if negative else
              "Gunakan " + " / ".join(names) + " sebagai dasar penawaran; batasi muatan sesuai kapasitas." if limited else
              "Gunakan " + " / ".join(names) + " sebagai dasar penawaran.")
    reasons = ["LOWEST_COST_FEASIBLE_NOMINAL"]
    if limited:
        reasons.append("UPPER_TOLERANCE_NOT_FULLY_FEASIBLE")
    if negative:
        reasons.append("SELLING_RATE_BELOW_MODELED_COST")
    if quote is None:
        reasons.append("COST_FLOOR_NOT_PROFIT_FORECAST")
    if len(names) > 1:
        reasons.append("EQUAL_COST_OPTIONS")
    if incomplete:
        reasons.append("VESSEL_INPUT_INCOMPLETE")
        action += " Lengkapi input " + " / ".join(incomplete) + " untuk membandingkan kedua kelas."
    return {"action": action, "status": "REPRICE" if negative else "PREPARE_OFFER",
            "selected": names, "reasons": reasons}
