"""Commercial Brief sections for the optional risk assessment."""
from pilog_cfr_dss.models.risk import AGREEMENTS, BASES, STATUSES, STRESSES
from pilog_cfr_dss.reporting.formatting import number_text as n


LABELS = {**{key: label for key, (label, _) in STRESSES.items()}, "physical": "Kelayakan muatan dan draft",
          "fx": "Kurs", "liability": "Tanggung jawab maritim"}
CASE_WIDE = {"physical_freight", "fx", "liability"}


def risk_records(analysis, section, keyed_rows):
    seen = set()
    for family, details in analysis["classes"].items():
        for key, row in keyed_rows(details[section]):
            if key in CASE_WIDE:
                if key in seen:
                    continue
                seen.add(key)
                yield "Voyage", key, row
            else:
                yield family, key, row


def exposure_lines(result, clean):
    analysis = result["risk_assessment"]
    inputs = result["case"]["risk_assessment"]
    lines = ["", "### Komitmen pada voyage ini", "",
             "| Transaksi | Status | Dasar harga | Cakupan tetap (%) | Tarif tercatat | Tanggal / berlaku sampai | Rujukan |",
             "|---|---|---|---:|---|---|---|"]
    for key, label in AGREEMENTS.items():
        item = inputs.get("commitments", {}).get(key, {})
        if key == "charter" and item.get("vessel_class"):
            label += " · " + item["vessel_class"]
        dates = " / ".join(item.get(key) or "—" for key in ("agreed_on", "valid_until"))
        rate = "—" if not item.get("rate") else n(item["rate"]) + (" USD/hari" if key == "charter" else " USD/MT")
        lines.append(f"| {label} | {STATUSES[item.get('status', 'unknown')]} | {BASES[item.get('basis', 'unknown')]} | "
                     f"{n(item.get('coverage_percent'))} | {rate} | {clean(dates)} | {clean(item.get('evidence') or '—')} |")
    if inputs.get("vessel_nominated") is not None:
        lines += ["", "Nominasi kapal: " + ("sudah" if inputs["vessel_nominated"] else "belum") + "."]
    sources = [(label, inputs.get(key, {}).get("evidence")) for key, label in
               (("VLSFO", "VLSFO"), ("LSMGO", "LSMGO"), ("port_delay", "Tambahan hari di pelabuhan"))]
    sources += [(label, inputs.get(key)) for key, label in (("fx_evidence", "Kurs"), ("liability_evidence", "P&I"))]
    if any(source for _, source in sources):
        lines += ["", *(f"- {label}: {clean(source)}" for label, source in sources if source)]
    if not analysis["scope_matches"]:
        lines += ["", "**Periksa ulang cakupan komitmen.** Rute, muatan, komoditas, atau jadwal berbeda dari kasus yang dicatat."]
    lines += ["", "| Kapal | Risiko | Penanggung | Status | Porsi terbuka (%) | Dasar |", "|---|---|---|---|---:|---|"]
    for family, key, row in risk_records(analysis, "exposures", dict.items):
        lines.append(f"| {family} | {LABELS[key]} | {row['owner'] or '—'} | {row['status']} | "
                     f"{n(row['open_percent'])} | {clean(row['reason'])} |")
    return lines


def action_lines(analysis):
    lines = ["", "### Opsi mitigasi", "", "| Kapal | Risiko | Penanggung tindakan | Tindakan dan syarat |",
             "|---|---|---|---|"]
    options = [(row["priority"], family, key, row) for family, key, row in
               risk_records(analysis, "exposures", dict.items) if row["open_share"] != 0]
    for _, family, key, row in sorted(options, key=lambda item: item[0]):
        lines.append(f"| {family} | {LABELS[key]} | {row['team']} | {row['action']} |")
        for option, conditions in row["options"]:
            lines.append(f"| {family} | {LABELS[key]} | {row['team']} | **{option}.** {conditions} |")
    return lines if options else []


def stress_lines(analysis, clean):
    lines = []
    for family, details in analysis["classes"].items():
        hire = details["exposures"]["hire"]
        cutoff = hire["break_even_usd_day"]
        if cutoff is not None:
            lines += ["", f"**Hire impas {family}: {n(cutoff)} USD/hari** untuk durasi, biaya, dan tarif yang tercatat."]
        if "quote_usd_day" in hire:
            validity = f" Berlaku sampai {hire['quote_valid_until']}." if hire["quote_valid_until"] else " Konfirmasi masa berlaku."
            lines += [f"Quotation tercatat {n(hire['quote_usd_day'])} USD/hari; selisih terhadap impas "
                      f"{n(hire['quote_gap_usd_day'])} USD/hari.{validity}"]
    stresses = list(risk_records(analysis, "scenarios", lambda rows: ((row["driver"], row) for row in rows)))
    if stresses:
        lines += ["", "### Uji perubahan", "", "Setiap baris mengubah satu input. Baca dampak freight fisik PI dan hire PILOG secara terpisah.", "",
                  "| Kapal | Skenario | Basis dan pos terdampak | Δ USD | Δ USD/MT | Δ hari | Surplus/defisit USD |",
                  "|---|---|---|---:|---:|---:|---:|"]
        for family, key, row in stresses:
            label, unit = STRESSES[key]
            status = row.get("status") or f"{row['metric']} · {row['basis']}"
            if row.get("margin_basis"):
                status += " · " + row["margin_basis"]
            if row.get("exposed_cargo_mt") is not None:
                status += f" · {n(row['exposed_cargo_mt'])} MT"
            if row.get("stressed_rate") is not None:
                status += f" · {n(row['baseline_rate'])} → {n(row['stressed_rate'])} USD/hari"
            if row["driver"] in ("cargo", "draft"):
                limit = row.get("limit_mt", row.get("capacity_limit_mt"))
                if limit is not None:
                    status += f" · Batas {n(limit)} MT"
            lines.append(f"| {family} | {label} {n(row['change'])} {unit} | {clean(status)} | "
                         f"{n(row.get('delta_usd'))} | {n(row.get('delta_usd_mt'))} | {n(row.get('delta_days'))} | {n(row.get('surplus_usd'))} |")
    if analysis["demurrage_entered"]:
        claims = analysis["demurrage"]
        if all(claims[key] is None for key in ("payable_usd", "recoverable_usd")):
            lines += ["", "Lengkapi penanggung tambahan hari, dasar klaim, dan rujukan klausul sebelum memakai estimasi demurrage."]
        else:
            lines += ["", f"Demurrage terutang {n(claims['payable_usd'])} USD; dapat ditagih {n(claims['recoverable_usd'])} USD. "
                      f"Dasar: {clean(claims['basis'])}. Rujukan: {clean(claims['evidence'])}. Keduanya dicatat terpisah dari biaya operasi."]
    return lines
