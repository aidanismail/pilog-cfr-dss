"""Explainable tender eligibility and CFR execution rules, not tender awards."""
from decimal import Decimal
from typing import Any
from pilog_cfr_dss.calculations.capacity import gross_dwt_screen
from pilog_cfr_dss.models.iteration_04 import Case04
from pilog_cfr_dss.validation.iteration_04 import timestamp


def risk_label(contribution: Decimal) -> str:
    return "Dapat rugi" if contribution < 0 else "Impas" if contribution == 0 else "Tidak negatif"


def evaluate_tender(rows: list[dict[str, Any]], context: dict[str, Any]) -> dict[str, Any]:
    from pilog_cfr_dss.models.tender_clock import bid_in_round
    cutoff = timestamp(context["evaluation_cutoff"])
    clock = context.get("auction_clock")
    in_window = lambda r: clock is None or bid_in_round(r, clock)
    considered = [r for r in rows if ("submitted_at" not in r or timestamp(r["submitted_at"]) <= cutoff) and in_window(r)]
    latest = {}
    order = (lambda r: (timestamp(r["submitted_at"]), r["round"], r["sequence"], r["bid_id"])) if clock else (
        lambda r: (r["round"], r["sequence"], r["bid_id"]))
    for row in sorted(considered, key=order):
        latest[row["buyer_id"]] = row["bid_id"]
    evaluated = []
    for row in rows:
        current = latest.get(row["buyer_id"]) == row["bid_id"]
        in_time = "submitted_at" not in row or timestamp(row["submitted_at"]) <= cutoff
        not_expired = "valid_until" not in row or timestamp(row["valid_until"]) >= cutoff
        within_round = in_window(row)
        active = current and in_time and within_round and not_expired and row["status"] == "active"
        eligible = active and row["oe_gap_usd_mt"] >= 0
        reason = ("Lolos floor PI" if eligible else "FOB di bawah OE/HPS" if active
                  else "Di luar jendela 3 menit putaran" if not within_round else "Di luar cutoff" if not in_time else "Bid sudah diganti" if not current
                  else "Bid kedaluwarsa" if not not_expired else f"Status bid: {row['status']}")
        evaluated.append({**row, "is_latest": current, "is_active_at_cutoff": active,
                          "eligible": eligible, "reason": reason})
    ranked = sorted((r for r in evaluated if r["eligible"]), key=lambda r: (-r["fob_usd_mt"], r["buyer_id"], r["bid_id"]))
    top = [r["bid_id"] for r in ranked if r["fob_usd_mt"] == ranked[0]["fob_usd_mt"]] if ranked else []
    # Competition ranking: tied prices share a rank; sorting IDs is not an award.
    rank, previous_price = None, None
    for position, row in enumerate(ranked, 1):
        if row["fob_usd_mt"] != previous_price:
            rank, previous_price = position, row["fob_usd_mt"]
        row["eligible_rank"] = rank
    for row in evaluated:
        row.setdefault("eligible_rank", None)
    selection = context.get("pi_selected_bid_id")
    selected_valid = selection is None or any(r["bid_id"] == selection for r in ranked)
    candidates = ([selection] if selected_valid else []) if selection is not None else top
    latest_rows = [r for r in evaluated if r["is_latest"]]
    active_rows = [r for r in latest_rows if r["is_active_at_cutoff"]]
    best_active = max(active_rows, key=lambda r: r["fob_usd_mt"]) if active_rows else None
    return {"bids": evaluated, "latest_bids": latest_rows, "best_active_bid": best_active,
            "ranking": [r["bid_id"] for r in ranked], "top_tied_bid_ids": top,
            "candidate_bid_ids": candidates, "pi_selected_bid_id": selection,
            "selection_valid": selected_valid, "gate_a_pass": bool(ranked) and selected_valid,
            "award_status": "NOT_AWARDED_BY_SYSTEM"}


def decide(case: Case04, tender: dict[str, Any], baseline: dict[str, Decimal],
           scenarios: list[dict[str, Any]]) -> dict[str, Any]:
    bounds = case.context["vessel_policy"][case.values["vessel_class"]]
    vessel_ok, vessel_reason = gross_dwt_screen(case.number("dwt_mt"), case.number("cargo_mt"),
                                               Decimal(str(bounds[0])), Decimal(str(bounds[1])))
    # Gross-DWT screen only. No unprovided terminal/availability/laycan assurance.
    floor_ok = tender["gate_a_pass"]
    contribution_ok = baseline["contribution_usd"] >= 0
    gate_b = "NOT_EVALUATED" if not floor_ok else "PASS" if vessel_ok and contribution_ok else "FAIL"
    action = "GO" if floor_ok and gate_b == "PASS" else "NO_GO"
    reasons = []
    if not floor_ok:
        reasons.append("NO_ELIGIBLE_ACTIVE_BID" if tender["selection_valid"] else "PI_SELECTION_NOT_ELIGIBLE")
    elif not vessel_ok:
        reasons.append(vessel_reason)
    if floor_ok and not contribution_ok:
        reasons.append("NEGATIVE_BASELINE_CONTRIBUTION")
    if action == "GO":
        reasons.append("BASELINE_BREAK_EVEN" if baseline["contribution_usd"] == 0 else "BASELINE_NONNEGATIVE")
    negative_stress = [s["scenario_id"] for s in scenarios if s["economics"]["contribution_usd"] < 0]
    if action == "GO" and negative_stress:
        reasons.append("STRESS_LOSS_DISCLOSED_NOT_VETO")
    candidate = next((r for r in tender["bids"] if r["bid_id"] in tender["candidate_bid_ids"]), None)
    active_rows = [r for r in tender["bids"] if r["is_active_at_cutoff"]]
    selected = next((r for r in tender["bids"] if r["bid_id"] == tender["pi_selected_bid_id"]), None)
    price_row = selected or candidate or (max(active_rows, key=lambda r: r["fob_usd_mt"]) if active_rows else None)
    active_ok = selected["is_active_at_cutoff"] if selected is not None else bool(active_rows)
    price_ok = price_row is not None and price_row["oe_gap_usd_mt"] >= 0
    floor_evidence = (f"{price_row['buyer_id']}/{price_row['bid_id']}: FOB {price_row['fob_usd_mt']} / OE/HPS {case.context['oe_hps']['value']} USD/MT"
                      if price_row is not None else "Tidak ada bid aktif untuk dicek terhadap floor PI.")
    checks = [
        {"name": "Input hitungan penting", "status": "Lolos", "evidence": "Angka dan satuan valid; perbedaan tahun hanya catatan."},
        {"name": "Bid terakhir masih berlaku", "status": "Lolos" if active_ok else "Tidak lolos", "evidence": "Ada bid terakhir aktif pada cutoff kasus." if active_ok else "Bid tidak aktif/pilihan PI sudah tidak berlaku."},
        {"name": "Harga barang memenuhi PI", "status": "Belum dapat dicek" if price_row is None else "Lolos" if price_ok else "Tidak lolos", "evidence": floor_evidence},
        {"name": "Kapasitas — screen awal", "status": "Belum dievaluasi" if not floor_ok else "Lolos" if vessel_ok else "Tidak lolos", "evidence": f"Cargo {case.values['cargo_mt']} MT; DWT {case.values['dwt_mt']} MT. Belum membuktikan DWCC/terminal/availability."},
        {"name": "Kontribusi baseline", "status": "Belum dievaluasi" if not floor_ok else "Lolos" if contribution_ok else "Tidak lolos", "value_usd": baseline["contribution_usd"], "evidence": str(baseline["contribution_usd"]) + " USD/pengiriman" + ("; indikatif, Gate B belum dievaluasi karena Gate A gagal." if not floor_ok else "")},
    ]
    human_reasons = []
    if not floor_ok:
        human_reasons.append("tidak ada bid terakhir aktif yang memenuhi syarat PI" if tender["selection_valid"] else "bid pilihan PI tidak lagi memenuhi syarat")
    if floor_ok and not vessel_ok:
        human_reasons.append("kapal tidak lolos screen awal kapasitas/kelas")
    if floor_ok and not contribution_ok:
        human_reasons.append("kontribusi freight baseline negatif")
    summary = ("Harga barang memenuhi OE/HPS; screen awal kapal lolos dan kontribusi freight baseline tidak negatif."
               if action == "GO" else "CFR belum layak diteruskan karena " + "; ".join(human_reasons) + ".")
    if action == "GO" and negative_stress:
        summary += " Risiko rugi tetap perlu ditinjau sebelum komitmen manusia."
    next_steps = prescriptions(tender, action, floor_ok, vessel_ok, contribution_ok,
                               baseline["contribution_usd"], negative_stress)
    # Presentation cause only: it explains the existing result, never sets a gate.
    cause = ("GO_BREAK_EVEN" if baseline["contribution_usd"] == 0 else "GO_POSITIVE") if action == "GO" else (
        "PI_SELECTION" if not tender["selection_valid"] else
        "NO_ACTIVE_BID" if not floor_ok and tender["best_active_bid"] is None else
        "TENDER_FLOOR" if not floor_ok else
        "VESSEL_AND_ECONOMICS" if not vessel_ok and not contribution_ok else
        "VESSEL_SCREEN" if not vessel_ok else "NEGATIVE_ECONOMICS")
    by_id = {row["bid_id"]: row for row in tender["bids"]}
    stress_rows = [row for row in scenarios if row["scenario_id"] != "baseline"]
    brief_context = {
        "cause": cause,
        "candidate_bids": [by_id[bid_id] for bid_id in tender["candidate_bid_ids"]],
        "price_reference_bid": price_row,
        "selection_basis": "PI_SELECTION" if tender["pi_selected_bid_id"] is not None else "RANKING_NOT_AWARD",
        "primary_stress": min(stress_rows, key=lambda row: row["economics"]["contribution_usd"]) if stress_rows else None,
        "economics_is_decision_evidence": floor_ok,
        "emphasize_economics": floor_ok and (action == "GO" or not contribution_ok),
    }
    return {"action": action, "summary": summary, "reason_codes": reasons,
            "gate_a": "PASS" if floor_ok else "FAIL", "gate_b": gate_b, "checks": checks,
            "negative_stress_ids": negative_stress, "next_steps": next_steps,
            "brief_context": brief_context,
            "human_approval": "PENDING_HUMAN_REVIEW",
            "vessel_screen": {"passed": vessel_ok, "reason": vessel_reason, "scope": "gross_DWT_only", "used_for_decision": floor_ok}}


def prescriptions(tender: dict[str, Any], action: str, floor_ok: bool, vessel_ok: bool,
                  contribution_ok: bool, contribution: Decimal,
                  negative_stress: list[str]) -> list[dict[str, str]]:
    """Human actions by evaluated cause; no automatic repricing, bid or award."""
    steps = []

    def add(code: str, role: str, text: str) -> None:
        steps.append(review_step(code, role, text))

    if not floor_ok:
        if not tender["selection_valid"]:
            add("REVIEW_PI_SELECTION", "PI", "Tinjau bid pilihan PI yang tidak eligible; jangan meneruskan pilihan ini atau menggantinya otomatis dengan ranking lain.")
        elif tender["best_active_bid"] is None:
            add("REVIEW_BID_VALIDITY", "PI", "Tidak ada bid terakhir aktif pada cutoff. Tinjau status/masa berlaku atau putaran tender berikut; jangan menghidupkan bid lama.")
        else:
            add("REVIEW_TENDER_FLOOR", "PI", "Bid aktif terbaik belum memenuhi OE/HPS. Tinjau putaran tender berikut; gunakan shortfall dan alpha minimum hanya sebagai analisis internal, bukan aturan alpha untuk buyer.")
        add("DO_NOT_EXECUTE_GATE_B", "PI/PILOG", "Jangan lanjutkan pelaksanaan dari kasus ini. Gate B belum dievaluasi; angka freight hanya diagnostik sampai ada kandidat memenuhi syarat.")
    else:
        if not vessel_ok:
            add("REVIEW_VESSEL_SCREEN", "PILOG", "Tinjau cargo, profil dan kelas kapal yang gagal screen awal; jangan mengasumsikan kapal pengganti, DWCC atau availability tanpa data.")
        if not contribution_ok:
            add("REVIEW_BASELINE_COST", "PILOG", "Freight tetap tidak menutup biaya baseline setelah komisi. Tinjau biaya/operasi dan jalankan ulang; jangan menaikkan harga tender secara otomatis agar GO.")
        if action == "GO":
            if contribution == 0:
                add("REVIEW_ZERO_BUFFER", "PI/PILOG", "Baseline tepat impas: lolos aturan, tetapi tidak ada buffer kontribusi positif. Bahas dampak perubahan biaya sebelum persetujuan manusia.")
            else:
                add("REVIEW_CANDIDATE", "PI/PILOG", "Ajukan kandidat, freight tetap dan cakupan biaya untuk review. Kontribusi positif model bukan laba bersih atau award tender.")
            if len(tender["top_tied_bid_ids"]) > 1 and tender["pi_selected_bid_id"] is None:
                add("REVIEW_TIE", "PI", "Ada bid peringkat tertinggi yang seri. PI meninjau pilihan; sistem tidak menentukan pemenang di antara bid seri.")
            if negative_stress:
                add("REVIEW_STRESS_LOSS", "PILOG", "Bahas skenario rugi yang ditampilkan. Stress bukan veto otomatis; jika perubahan itu menjadi baseline, evaluasi ulang dengan freight tender tetap.")
            add("REVIEW_OPERATIONAL_READINESS", "PILOG", "Verifikasi kesiapan kapal aktual, DWCC, terminal, jadwal/laycan dan availability sebelum komitmen; screen DWT belum membuktikannya.")
    return steps


_REVIEW_REQUIREMENTS = {
    "REVIEW_PI_SELECTION": (
        "Catatan PI tentang bid yang ditinjau dan status kelayakannya; bukan penggantian kandidat otomatis.",
        "Pilihan PI, status bid atau penawaran berubah."),
    "REVIEW_BID_VALIDITY": (
        "Bid terakhir yang aktif pada cutoff atau keputusan PI mengenai putaran berikutnya.",
        "Ada bid/status/masa berlaku atau cutoff kasus baru."),
    "REVIEW_TENDER_FLOOR": (
        "Hasil peninjauan langkah tender berikut; penawaran baru harus dinilai kembali terhadap floor PI.",
        "Alpha, status bid, indeks atau OE/HPS kasus berubah; freight tidak otomatis direvisi."),
    "DO_NOT_EXECUTE_GATE_B": (
        "Catatan bahwa belum ada kandidat layak diteruskan dari kasus ini; angka freight hanya diagnostik.",
        "Kandidat tender memenuhi syarat dan kasus dievaluasi ulang."),
    "REVIEW_VESSEL_SCREEN": (
        "Penjelasan/perbaikan profil kapal, kelas atau quantity yang gagal screen; tidak mengasumsikan kapal tersedia.",
        "Cargo atau profil kapal yang digunakan berubah."),
    "REVIEW_BASELINE_COST": (
        "Rincian biaya/durasi yang ditinjau dan baseline revisi bila diperlukan; jangan menaikkan freight diam-diam.",
        "Estimasi biaya, durasi atau rencana operasi berubah; gunakan freight tetap kecuali penawaran direvisi manusia."),
    "REVIEW_ZERO_BUFFER": (
        "Catatan keputusan manusia atas baseline impas tanpa buffer positif, berikut asumsi biaya yang ditinjau.",
        "Biaya atau durasi dasar berubah."),
    "REVIEW_CANDIDATE": (
        "PI: catatan kandidat tender. PILOG: hasil review ekonomi satu pengiriman; bukan award sistem.",
        "Bid/pilihan PI, quantity atau basis ekonomi berubah."),
    "REVIEW_TIE": (
        "Catatan PI tentang pilihan di antara bid seri; tidak ada pemenang yang ditetapkan oleh urutan ID.",
        "Pilihan PI atau bid berikutnya tersedia."),
    "REVIEW_STRESS_LOSS": (
        "Konfirmasi/revisi durasi/biaya dan catatan penanganan risiko residual sebelum komitmen.",
        "Durasi/biaya stress menjadi baseline; freight tetap."),
    "REVIEW_OPERATIONAL_READINESS": (
        "Status berbukti kapal/DWCC, terminal, jadwal/laycan dan availability; yang belum ada ditandai belum terbukti.",
        "Kapal, jadwal, terminal atau rencana operasi berubah."),
    "CORRECT_CRITICAL_INPUT": (
        "Input field/unit/struktur yang dikoreksi dan hasil evaluasi ulang, tanpa nilai nol pengganti.",
        "Input yang dilaporkan bermasalah telah diperbaiki."),
}


def review_step(code: str, role: str, text: str) -> dict[str, str]:
    """Requested human review deliverables, not an approval or new eligibility rule."""
    deliverable, trigger = _REVIEW_REQUIREMENTS[code]
    return {"code": code, "review_role": role, "text": text,
            "deliverable": deliverable, "re_evaluate_when": trigger,
            "review_evidence_status": "NOT_RECORDED_IN_SIMULATION"}
