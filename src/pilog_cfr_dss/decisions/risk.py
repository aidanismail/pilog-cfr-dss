"""Map documented transaction commitments to risk owners and follow-up options."""
from decimal import Decimal


ZERO, FULL = Decimal(0), Decimal(1)
FFA_CHECKS = "Cocokkan indeks, rute, kelas, unit, bulan settlement, likuiditas dan pendanaan. Konfirmasi kewenangan Treasury."


def fixed_share(agreement):
    if agreement["status"] == "open" and agreement["evidence"]:
        return ZERO
    if (agreement["status"] == "binding" and agreement["basis"] == "fixed"
            and agreement["evidence"] and agreement["coverage"] is not None):
        return agreement["coverage"] / 100
    return None


def overlap(fixed, exposed_against):
    """Use known overlap only. Two partial commitments need matching scope evidence."""
    if fixed == FULL or exposed_against == ZERO:
        return ZERO
    if fixed is None or exposed_against is None:
        return None
    if fixed == ZERO or exposed_against == FULL:
        return min(FULL - fixed, exposed_against)
    return None


def risk_rows(risk, row, max_row, cutoff):
    family = row["vessel_class"]
    cfr, freight, charter = (risk["commitments"][key] for key in ("cfr", "freight", "charter"))
    cfr_share, freight_share, charter_share = map(fixed_share, (cfr, freight, charter))
    if risk["charter_class"] != family or not risk["scope_matches"]:
        charter_share = None
    if not risk["scope_matches"]:
        cfr_share = freight_share = None
    commercial = row.get("commercial")
    hire_matches = charter["rate"] is None or charter_share == ZERO or charter["rate"] == row.get("hire_rate_usd_day")
    freight_matches = bool(commercial and freight["rate"] == commercial["selling_freight_usd_mt"])
    rows = {}

    def add(key, owner, share, reason, action, options=(), team="Commercial/Chartering PILOG", priority=40):
        status = "Perlu konfirmasi" if share is None else "Tidak ada sisa exposure teridentifikasi" if share == 0 else "Terbuka"
        rows[key] = {"owner": owner if share else "", "status": status, "open_share": share,
                     "open_percent": None if share is None else share * 100, "reason": reason,
                     "action": action, "options": list(options), "team": team, "priority": priority}

    pi_open = overlap(freight_share, cfr_share)
    pi_reason = "Penjualan CFR tetap telah mengikat; tarif freight PI masih terbuka pada porsi ini."
    if pi_open is None:
        pi_reason = "Cek status CFR, perjanjian freight, klausul penyesuaian dan irisan volume."
    elif pi_open == 0:
        pi_reason = ("Freight PI telah dikunci pada basis kasus." if freight_share == FULL
                     else "Belum ada porsi jual CFR tetap yang tercatat mengikat.")
    add("physical_freight", "PI", pi_open, pi_reason,
        "Kunci pembelian freight sesuai volume dan periode CFR." if pi_open else
        "Konfirmasi status harga CFR dan cakupan freight yang dibayar PI.",
        [("Kajian beli FFA", FFA_CHECKS)] if pi_open else [], "Commercial PI", 10)

    hire_open = overlap(charter_share, freight_share)
    if freight_share not in (None, ZERO, FULL) and charter_share != FULL:
        hire_open = None  # freight volume alone does not determine the hire days it covers
    hire_reason = "Tarif jasa PILOG telah mengikat; hire masih terbuka pada porsi ini."
    if hire_open is None:
        hire_reason = "Cocokkan status sewa, waktu yang dicakup, dan perjanjian jasa PILOG."
        if freight_share not in (None, ZERO, FULL):
            hire_reason += " Hubungkan volume freight parsial dengan hari sewa sebelum mengalokasikan biaya."
    elif hire_open == 0:
        hire_reason = ("Hire tetap pada periode yang dicakup. Periksa risiko tambahan hari secara terpisah."
                       if charter_share == FULL else "Belum ada porsi tarif jasa tetap yang tercatat mengikat.")
    if charter_share and not hire_matches:
        hire_reason += " Hire yang dicatat di kontrak berbeda dari input kalkulator."
    add("hire", "PILOG", hire_open, hire_reason,
        "Minta quotation sewa yang mengikat dan bandingkan dengan batas hire impas." if hire_open else
        "Konfirmasi periode sewa dan ketentuan biaya sebelum mengikat penawaran.",
        [("Kajian beli FFA", FFA_CHECKS)] if hire_open else [], priority=5)
    rows["hire"]["margin_matches"] = freight_matches and hire_matches and freight_share == FULL
    rows["hire"]["break_even_usd_day"] = cutoff if rows["hire"]["margin_matches"] and hire_open == FULL else None
    if (rows["hire"]["break_even_usd_day"] is not None and risk["quote_comparable"]
            and charter["status"] == "open" and charter["rate"] is not None and charter["rate"] > 0):
        rows["hire"].update(quote_usd_day=charter["rate"], quote_gap_usd_day=charter["rate"] - cutoff,
                            quote_valid_until=charter["valid_until"])

    selling_open = overlap(freight_share, charter_share)
    if charter_share not in (None, ZERO, FULL) and freight_share != FULL:
        selling_open = None
    options = [("Kajian jual FFA", FFA_CHECKS + " Kapasitas tanpa kargo tetap perlu ditangani secara fisik.")]
    if risk["recurring_program"]:
        options.insert(0, ("COA bertarif tetap", "Cocokkan volume minimum, rute, jadwal dan klausul penyesuaian."))
    add("selling_freight", "PILOG", selling_open,
        "Sewa telah mengikat; kargo atau pendapatan jasa masih terbuka." if selling_open else
        "Cek cakupan sewa dan komitmen kargo sebelum menilai risiko penurunan tarif jual.",
        "Amankan komitmen kargo atau siapkan pemakaian kapal alternatif.", options if selling_open else [], priority=15)

    for grade in ("VLSFO", "LSMGO"):
        bunker = risk[grade]
        share = fixed_share(bunker) if bunker["evidence"] and bunker["payer"] != "unknown" and risk["scope_matches"] else None
        add(grade, bunker["payer"], None if share is None else FULL - share,
            "Konfirmasi penanggung biaya, grade, lokasi, volume dan periode pembelian." if share is None else
            "Porsi mencakup kebutuhan bahan bakar pada voyage dan basis pembelian ini.",
            f"Cek quotation harga tetap {grade} untuk volume terbuka.",
            [("Kajian pay-fixed bunker swap", "Cocokkan grade, harga acuan, lokasi, periode, volume dan kewenangan."),
             ("Kajian call option", "Bandingkan strike, premi, basis dan volume."),
             ("Klausul penyesuaian bunker", "Cek formula, batas penyesuaian dan persetujuan kontrak.")] if share is not None and share < FULL else [])

    delay = risk["port_delay"]
    for key in ("load_wait", "discharge_wait"):
        identified = delay["evidence"] and delay["payer"] != "unknown" and risk["scope_matches"]
        add(key, delay["payer"], FULL if identified else None,
            "Tambahan durasi dihitung terpisah dari perubahan tarif hire. Hak klaim mengikuti kontrak.",
            "Konfirmasi waktu terminal dan selaraskan laytime serta demurrage pada kontrak terkait.", team="Operations PILOG")

    capacity = row.get("capacity", {})
    if (not row["feasible"] or not max_row["feasible"] or any(check["status"] not in ("PASS", "ESTIMATED_PASS")
            for check in capacity.get("checks", []))):
        add("physical", "PILOG", None, "Periksa berat, ruang palka, draft dan batas atas tolerance.",
            "Konfirmasi kelayakan muatan dan terminal, atau ubah kelas kapal sebelum penawaran.",
            team="Operations PILOG", priority=0 if not row["feasible"] else 20)
        rows["physical"]["owner"] = "PILOG"
    if risk["fx_evidence"] and risk["scope_matches"]:
        add("fx", "", None, "Arus kas berbeda mata uang perlu dicocokkan pada entitas dan jatuh tempo yang sama.",
            "Cocokkan penerimaan dan pembayaran; ajukan sisa exposure untuk kajian FX forward.", team="Finance/Treasury")
    if risk["liability_evidence"] and risk["scope_matches"]:
        add("liability", "", None, "Cakupan polis bergantung pada pihak tertanggung dan batas perlindungan.",
            "Periksa P&I dan perlindungan tanggung jawab charterer sesuai polis.", team="Legal/Insurance")
    # Retain an evidence prompt for incomplete commercial commitments and for inputs the user interacted with.
    for key in ("VLSFO", "LSMGO", "load_wait", "discharge_wait"):
        contract_key = "port_delay" if key.endswith("wait") else key
        if key not in risk["stresses"] and not risk[contract_key]["evidence"]:
            rows.pop(key)
    return rows
