"""Stakeholder decision brief: presentation only; all amounts come from calculations."""
import json
import re
from decimal import Decimal
from typing import Any
from pilog_cfr_dss.reporting.formatting import price_time, number_text, percent_text


def clean(value: Any) -> str:
    return str(value).replace("|", "/").replace("\n", " ").replace("\r", " ")


def amount(value: Any, *, minimum=False) -> str:
    return number_text(value, minimum=minimum)


def price_time_lines(report: dict) -> list[str]:
    records = report.get("price_records")
    if not records:
        return []
    pricing, freight = report["pricing"], records["freight"]
    context = report["input_lineage"]["context"]
    snapshot = context["market_snapshot"]
    lines = ["", "### Waktu dan sumber harga", "",
        "Harga dalam tabel bid dihitung " + price_time(pricing.get("calculated_at")) + ".",
        "Freight ditetapkan " + price_time(freight.get("fixed_at")) + "; perhitungan ulang tidak mengubah waktu penetapan tersebut.",
        "Data pasar diambil " + price_time(snapshot["fetched_at"]) + ". Tanggal observasi bukan waktu pengambilan data.", "",
        "| Acuan pasar | Nilai | Satuan | Tanggal data | Pemakaian |", "|---|---:|---|---|---|"]
    profile = context["vessel_profile"]
    manual = context["pricing"]["target_tce"].get("source_status") == "simulation_only_user_input"
    for family, quote in snapshot["tc_rates"].items():
        used = family == profile["market_family"] and not manual
        lines.append(f"| {clean(quote['series'])}, 1-year T/C | {amount(quote['value'])} | {quote['unit']} | {quote['source_observed_on']} | {'Target TCE' if used else 'Pembanding'} |")
    rows = {r["key"]: r for r in report["input_lineage"]["voyage_fields"]}
    overrides = context.get("cost_forecast", {}).get("overrides", {})
    for key, quote in snapshot["bunkers"].items():
        used = rows[key]["source_status"] != "simulation_only_user_input" and key not in overrides
        lines.append(f"| {clean(quote['series'])} | {amount(quote['value'])} | {quote['unit']} | {quote['source_observed_on']} | {'Biaya bunker' if used else 'Pembanding; input manual dipakai'} |")
    lines += ["", "Sumber pasar: Fearnpulse. Profil fisik: Voyage Estimate.xlsx, sheet " + clean(profile["sheet"]) + ".",
              "Tarif T/C dipakai sebagai target TCE net sebelum running berdasarkan asumsi; bukan hire tambahan atau quote voyage khusus."]
    if context.get("voyage_estimate"):
        estimate = context["voyage_estimate"]
        lines.append("Basis voyage: " + clean(estimate["label"]) + ", sheet " + clean(estimate["sheet"]) +
                     ". Muatan, produktivitas, waktu tunggu dan biaya pelabuhan adalah asumsi demo.")
    if profile["market_class_proxy"]:
        lines.append("Profil Handymax memakai acuan pasar Handysize 38k sebagai proxy kelas.")
    if context.get("auction_clock"):
        lines.append("Setiap putaran berdurasi tetap 3 menit. Bid pada/di luar waktu tutup putarannya tidak eligible; bid baru tidak memperpanjang waktu.")
    if overrides:
        lines.append("Estimasi biaya terbaru memakai override yang tercatat; benchmark awal tetap ditampilkan sebagai referensi, bukan bukti harga pembelian terbaru.")
    return lines


def executive_decision_lines(report: dict) -> list[str]:
    rec, review = report["recommendation"], report["commercial_review"]
    lines = ["**Cakupan keputusan: kelayakan ekonomi penawaran CFR; pelaksanaan kapal dan award tetap keputusan PI/PILOG.**"]
    if rec["gate_a"] != "PASS":
        return lines + decision_headline(report)
    rows = candidate_rows(report)
    subject = ", ".join(clean(row["buyer_id"]) + "/" + clean(row["bid_id"]) for row in rows)
    lines += ["Kandidat tender: **" + subject + "**; harga barang memenuhi OE/HPS."]
    if rec["action"] == "GO":
        lines.append("**GO: lanjutkan pembahasan komersial CFR berdasarkan ekonomi baseline.**")
    elif Decimal(review["loss_to_recover_usd"]) > 0:
        lines += [f"**NO GO: freight tetap tidak menutup biaya; estimasi rugi PILOG {amount(review['loss_to_recover_usd'])} USD.**",
                  "Bid barang yang tertinggi/lolos PI tidak menghilangkan kerugian freight PILOG."]
    else:
        lines.append("**NO GO: kapal gagal pemeriksaan awal kapasitas/kelas.**")
    if rec["gate_b"] == "FAIL" and not rec["vessel_screen"]["passed"] and Decimal(review["loss_to_recover_usd"]) > 0:
        lines.append("Kapasitas/kelas kapal juga tidak lolos; perbaikan biaya saja belum cukup untuk GO.")
    stress = rec.get("brief_context", {}).get("primary_stress")
    if stress:
        lines.append(f"Risiko utama yang dihitung: {clean(stress['label'])} → kontribusi {amount(stress['economics']['contribution_usd'])} USD. Skenario ini bukan prediksi.")
    lines.append("Tarif penawaran belum merupakan bukti penerimaan buyer; kesiapan kapal aktual belum ditetapkan oleh hasil ekonomi ini.")
    return lines


def cost_change_lines(report: dict) -> list[str]:
    if not report.get("commercial_review") or report["recommendation"]["gate_a"] != "PASS":
        return []
    review = report["commercial_review"]
    forecast = review["pricing_bridge"]["cost_forecast"]
    lines = ["", "### Dasar perubahan hasil", ""]
    if forecast:
        lines += ["Estimasi biaya diperbarui " + price_time(forecast["recorded_at"]) + ": " + clean(forecast["reason"]),
            "Harga freight dan bid dipertahankan; biaya awal dan histori tidak ditulis ulang.", "",
            "| Komponen biaya | Saat penetapan freight USD | Estimasi terbaru USD | Perubahan USD |", "|---|---:|---:|---:|"]
        labels = {"bunker_usd": "Bahan bakar", "port_other_usd": "Pelabuhan dan biaya lain", "running_usd": "Operasional kapal"}
        for row in review["drivers"]:
            lines.append(f"| {labels[row['component']]} | {amount(row['at_quote_usd'])} | {amount(row['current_usd'])} | {amount(row['change_usd'])} |")
        lines += ["", f"Kontribusi saat penetapan harga {amount(review['at_quote_contribution_usd'])} USD → saat ini {amount(review['current_contribution_usd'])} USD.", ""]
    else:
        lines.append("Ekonomi memakai biaya dasar saat penetapan penawaran; belum ada estimasi biaya terbaru yang terpisah.")
    lines.append(f"Kontribusi per hari voyage: **{amount(review['current_contribution_per_day_usd'])} USD/hari**.")
    if Decimal(review["loss_to_recover_usd"]) > 0:
        lines += ["", "**Opsi untuk dinilai manusia sebelum evaluasi ulang:**", "",
            f"- Kurangi biaya yang benar-benar dapat dihindari sedikitnya {amount(review['minimum_cost_reduction_usd'], minimum=True)} USD agar impas pada freight yang sama.",
            f"- Jika perlu penawaran baru, tarif impas sekurang-kurangnya {amount(review['break_even_offer_usd_mt'], minimum=True)} USD/MT. "
            "Ini hitungan hipotetis, bukan perubahan harga otomatis atau jaminan buyer setuju.",
            "- Jika biaya tidak dapat diperbaiki dan penawaran baru tidak disepakati, jangan lanjutkan berdasarkan kasus yang rugi ini.", "",
            "Angka pemulihan biaya dan tarif impas dibulatkan ke atas agar tidak menyisakan kerugian karena pembulatan."]
    return lines


def pricing_bridge_lines(report: dict) -> list[str]:
    review = report["commercial_review"]
    bridge = review["pricing_bridge"]
    benchmark = bridge["benchmark"] or {}
    target = bridge["target"]
    indicated = bridge.get("indication_at_fix_usd_mt")
    lines = ["", "### Asal tarif", "", "| Angka | Nilai | Fungsi |", "|---|---:|---|",
        f"| Benchmark pasar kapal | {amount(benchmark['value']) if benchmark.get('value') is not None else 'Tidak tersedia'} USD/hari | Referensi kelas/kontrak pasar |",
        f"| Target hasil harian sebelum operasional kapal | {amount(target['value'])} USD/hari | Input sasaran pricing, bukan biaya sewa tambahan |",
        f"| Indikasi saat penetapan harga | {amount(indicated) if indicated is not None else 'Tidak tercatat pada snapshot lama'} USD/MT | Tarif untuk mengejar target pada biaya awal |",
        f"| Freight penawaran tetap | {amount(bridge['fixed_offer_usd_mt']) if bridge['fixed_offer_usd_mt'] is not None else 'Belum ditetapkan'} USD/MT | Harga yang dipakai menilai bid dan kontribusi |",
        f"| Indikasi berdasarkan estimasi biaya sekarang | {amount(bridge['current_indication_usd_mt'])} USD/MT | Informasi; tidak mengganti penawaran tetap |",
        f"| Freight impas biaya sekarang | {amount(review['break_even_offer_usd_mt'], minimum=True)} USD/MT | Informasi, bukan minimum margin baru |", "",
        "Benchmark, target dan harga penawaran berbeda peran. Target-derived freight belum membuktikan daya saing/penerimaan pasar.",
        "### Waktu dan sumber harga", "",
        "Dihitung " + price_time(report["pricing"].get("calculated_at")) + "; freight ditetapkan " + price_time(bridge.get("fixed_at")) + "."]
    context = report["input_lineage"]["context"]
    snapshot = context.get("market_snapshot")
    if snapshot:
        lines.append("Fearnpulse diambil " + price_time(snapshot["fetched_at"]) + "; benchmark kapal " +
            clean(benchmark.get("source_observed_on", "tanggal tidak tersedia")) + "; tanggal bunker " +
            clean(", ".join(sorted({q['source_observed_on'] for q in snapshot['bunkers'].values()}))) + ".")
    if context.get("vessel_profile", {}).get("market_class_proxy"):
        lines.append("Handymax memakai proxy acuan pasar Handysize; kesesuaian kelas belum dinormalisasi menjadi quote Handymax.")
    if context.get("auction_clock"):
        lines.append("Putaran tetap 3 menit; penutupan dan cutoff mengikuti jadwal kasus, bukan award otomatis.")
    return lines


def identity_lines(report: dict[str, Any]) -> list[str]:
    return [
        f"Case: {clean(report['case_id'])}; run: {clean(report.get('run_id', 'Tidak tersedia — hasil belum disimpan/metadata historis'))}.",
        f"Dibuat (UTC): {clean(report.get('generated_at', 'Tidak tersedia'))}; cutoff tender: "
        f"{clean(report.get('input_lineage', {}).get('context', {}).get('evaluation_cutoff', 'Tidak tersedia'))}.",
        f"Brief {clean(report['report_version'])}; formula/rule {clean(report['version'])}.",
    ]


def candidate_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    rec = report["recommendation"]
    if "brief_context" in rec:
        return rec["brief_context"]["candidate_bids"]
    ids = report.get("tender", {}).get("candidate_bid_ids", [])
    by_id = {r["bid_id"]: r for r in report.get("tender", {}).get("bids", [])}
    return [by_id[bid_id] for bid_id in ids if bid_id in by_id]


def price_reference(report: dict[str, Any]) -> dict[str, Any] | None:
    tender = report["tender"]
    if not tender["selection_valid"]:
        return None
    candidates = candidate_rows(report)
    return candidates[0] if candidates else tender["best_active_bid"]


def emphasize_economics(rec: dict[str, Any]) -> bool:
    return rec.get("brief_context", {}).get("emphasize_economics", rec["gate_a"] == "PASS" and (
        rec["action"] == "GO" or "NEGATIVE_BASELINE_CONTRIBUTION" in rec["reason_codes"]))


def decision_headline(report: dict[str, Any]) -> list[str]:
    rec, base, tender = report["recommendation"], report["baseline"], report["tender"]
    candidates = candidate_rows(report)
    subject = ", ".join(f"{clean(r['buyer_id'])}/{clean(r['bid_id'])}" for r in candidates)
    if rec["gate_a"] != "PASS":
        lines = [clean(rec["summary"])]
        best = tender["best_active_bid"]
        if best is None:
            lines += ["Tidak ada bid aktif pada cutoff; best active bid dan shortfall tidak dapat dinyatakan."]
        else:
            floor_text = (f"kurang **{amount(best['floor_shortfall_usd_mt'])} USD/MT** terhadap OE/HPS"
                          if Decimal(best["floor_shortfall_usd_mt"]) > 0 else "memenuhi OE/HPS, tetapi tidak mengganti pilihan PI yang invalid")
            lines += [f"Penawaran aktif tertinggi: **{clean(best['buyer_id'])}/{clean(best['bid_id'])}**; "
                      f"FOB **{amount(best['fob_usd_mt'])} USD/MT**, {floor_text}. Bukan penawaran yang sudah diterima."]
        if tender["pi_selected_bid_id"] is not None:
            lines += [f"Bid pilihan PI **{clean(tender['pi_selected_bid_id'])}** tidak eligible; pilihan PI tidak diganti otomatis."]
        return lines + ["**Gate B belum dievaluasi.** Potensi pendapatan freight tidak membuat penawaran barang lolos harga minimum PI."]
    lines = [f"**Kandidat: {subject or 'Tidak tersedia'}.** " + (
        "Lanjutkan proses komersial CFR: harga barang memenuhi OE/HPS dan hasil neto freight tidak negatif."
        if rec["action"] == "GO" else clean(rec["summary"]))]
    if base["contribution_usd"] == "0" or Decimal(base["contribution_usd"]) == 0:
        lines += ["**Baseline tepat impas: hasil neto nol, bukan berarti untung dan tidak ada buffer positif.**"]
    if candidates:
        row = candidates[0]
        lines += [f"FOB **{amount(row['fob_usd_mt'])}** / OE/HPS **{amount(report['oe_hps_usd_mt'])} USD/MT**; "
                  f"freight **{amount(base['freight_usd_mt'])} USD/MT**."]
    risk = rec.get("brief_context", {}).get("primary_stress")
    if risk is not None and emphasize_economics(rec):
        lines += [f"Perhatian utama: **{clean(risk['label'])} → hasil neto {amount(risk['economics']['contribution_usd'])} USD** "
                  "(terendah dari skenario yang dihitung, bukan prediksi)."]
    return lines


def financial_lines(report: dict[str, Any]) -> list[str]:
    lines = ["### Estimasi pendapatan, biaya dan hasil neto", ""]
    financials = report.get("commercial_financials")
    if financials is None:
        return lines + ["Ringkasan nominal per pihak tidak tersedia pada hasil versi lama; lihat rincian perhitungan."]
    row = price_reference(report)
    totals = next((r for r in financials["bid_amounts"] if row is not None and r["bid_id"] == row["bid_id"]), None)
    if report["recommendation"]["action"] != "GO":
        lines += ["**Angka berikut hanya indikatif jika pengiriman terlaksana; bukan pendapatan terealisasi atau persetujuan melanjutkan.**", ""]
    if totals is not None:
        basis = "Kandidat" if candidate_rows(report) else "Acuan penawaran aktif; belum diterima"
        lines += [f"{basis}: {clean(row['buyer_id'])}/{clean(row['bid_id'])}; quantity {amount(financials['quantity_mt'])} MT.", ""]
    pi_gross = amount(totals["pi_goods_gross_revenue_usd"]) if totals is not None else "Tidak tersedia — belum ada acuan bid yang valid"
    p = financials["pilog"]
    fee = percent_text(report["pricing"]["commission_fraction"])
    net_label = "Hasil neto setelah biaya voyage dan komisi" if report["recommendation"]["action"] == "GO" else "Potensi hasil neto setelah biaya voyage dan komisi (jika terlaksana)"
    lines += ["Seluruh nominal dalam USD.", "",
              "| Komponen | PI — barang | PILOG — freight |", "|---|---:|---:|",
              f"| Estimasi pendapatan kotor | {pi_gross} | {amount(p['gross_revenue_usd'])} |",
              f"| Biaya voyage: bunker + port/other + running | — | {amount(p['voyage_cost_usd'])} |",
              f"| Komisi {fee} × gross freight revenue | — | {amount(p['commission_usd'])} |",
              f"| Total biaya/pengurang | Biaya barang tidak dimodelkan | {amount(p['total_deductions_usd'])} |",
              f"| **{net_label}** | **Tidak dihitung** | **{amount(p['net_after_voyage_usd'])}** |", "",
              "Pendapatan PI = FOB × quantity; pendapatan PILOG = freight × quantity. OE/HPS adalah batas harga barang, bukan biaya produksi.",
              "**Hasil neto PILOG = kontribusi freight, bukan laba bersih perusahaan.** Neto PI tidak dihitung karena biaya barang tidak dimodelkan."]
    return lines


def check_lines(rec: dict[str, Any]) -> list[str]:
    labels = {"PASS": "Lolos", "FAIL": "Tidak lolos", "NOT_EVALUATED": "Belum dievaluasi"}
    lines = ["### Pemeriksaan keputusan", "",
             f"**Gate A: {labels[rec['gate_a']]}; Gate B: {labels[rec['gate_b']]}.**", "",
             "| Pemeriksaan | Hasil | Bukti |", "|---|---|---|"]
    for check in rec["checks"]:
        evidence = check["evidence"]
        evidence = re.sub(r"(FOB |OE/HPS |Cargo |DWT )([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)",
                          lambda match: match.group(1) + amount(match.group(2)), evidence)
        if check["name"] == "Input hitungan penting" and check["status"] == "Lolos":
            evidence = "Angka dan satuan dapat dihitung."
        if "value_usd" in check:
            evidence = (amount(check["value_usd"]) + " USD hasil neto/pengiriman" if rec["gate_a"] == "PASS"
                        else "Tidak menjadi dasar melanjutkan karena Gate A gagal.")
        label = "Hasil neto PILOG" if check["name"] == "Kontribusi baseline" else check["name"]
        lines.append(f"| {clean(label)} | {clean(check['status'])} | {clean(evidence)} |")
    return lines


_ACTION_COPY = {
    "REVIEW_PI_SELECTION": "PI tetapkan pilihan bid yang masih memenuhi syarat; jangan ganti pilihan secara otomatis.",
    "REVIEW_BID_VALIDITY": "PI perbarui status/masa berlaku bid atau lanjutkan putaran tender; bid lama tidak dihidupkan kembali.",
    "REVIEW_TENDER_FLOOR": "PI lanjutkan langkah tender untuk memperoleh FOB yang memenuhi OE/HPS.",
    "DO_NOT_EXECUTE_GATE_B": "Jangan lanjutkan pengiriman berdasarkan penawaran ini; evaluasi kembali setelah kandidat memenuhi syarat.",
    "REVIEW_VESSEL_SCREEN": "PILOG sesuaikan cargo/profil kapal yang gagal cek kapasitas atau kelas, lalu hitung ulang.",
    "REVIEW_BASELINE_COST": "PILOG perbaiki rencana biaya/durasi dan hitung ulang; jangan menaikkan freight diam-diam agar hasil menjadi positif.",
    "REVIEW_ZERO_BUFFER": "Tetapkan keputusan komersial dengan kesadaran hasil tepat impas; setiap tambahan biaya dapat membuat rugi.",
    "REVIEW_CANDIDATE": "PI tetapkan kandidat/award sesuai kewenangan; PILOG gunakan hasil neto dan risiko pengiriman sebagai dasar keputusan.",
    "REVIEW_TIE": "PI putuskan pilihan di antara bid seri; sistem tidak menetapkan pemenang.",
    "REVIEW_STRESS_LOSS": "PILOG kendalikan durasi/biaya pelabuhan; hitung ulang dengan freight tetap jika kondisi risiko menjadi rencana dasar.",
    "REVIEW_OPERATIONAL_READINESS": "PILOG pastikan kapal, kapasitas muat aktual, terminal dan jadwal sebelum komitmen pengiriman.",
    "CORRECT_CRITICAL_INPUT": "Pemilik input koreksi field/satuan/struktur yang disebutkan, kemudian jalankan ulang.",
}


def action_lines(rec: dict[str, Any]) -> list[str]:
    lines = ["### Tindakan berikutnya", "", "| Pemilik | Tindakan |", "|---|---|"]
    for step in rec["next_steps"]:
        text = _ACTION_COPY.get(step["code"], step.get("deliverable", step["text"]))
        lines.append(f"| {clean(step['review_role'])} | {clean(text)} |")
    return lines


def exposure_lines(report: dict[str, Any]) -> list[str]:
    m, rec = report["metrics"], report["recommendation"]
    lines = ["## 2. Eksposur ekonomi (Exposure)", "",
             "Freight tetap membuat perubahan biaya BBM dan durasi ditanggung dalam hasil freight PILOG. "
             "Pada quantity, freight dan biaya yang sama, alpha tidak otomatis mengubah kontribusi freight PILOG; alpha mengubah harga barang PI."]
    if not emphasize_economics(rec):
        return lines + ["Potensi pendapatan dan hasil neto tidak menjadi dasar melewati pemeriksaan yang gagal. "
                        "Komitmen biaya aktual dan eksposur portofolio tidak dihitung."]
    descriptions = {"BASELINE_ALREADY_NEGATIVE": "Tidak berlaku — baseline sudah rugi",
                    "NO_INCREMENTAL_DAILY_COST_MODELLED": "Tidak dapat diturunkan — biaya harian tambahan model nol",
                    "BASELINE_BREAK_EVEN": "0 hari — baseline tepat impas"}
    buffer = descriptions.get(m["delay_buffer_status"])
    if buffer is None:
        buffer = f"Sekitar {amount(m['additional_port_days_to_break_even'])} hari tambahan"
    lines += ["", "| Ukuran | Nilai |", "|---|---:|",
              f"| Hasil neto per MT | {amount(m['contribution_per_mt_usd'])} USD/MT |",
              f"| Freight impas | {amount(report.get('commercial_review', {}).get('break_even_offer_usd_mt', m['freight_break_even_usd_mt']), minimum=True)} USD/MT |",
              f"| Tambahan biaya satu hari pelabuhan | {amount(m['incremental_port_day_usd'])} USD |",
              f"| Tambahan delay sampai impas | {buffer} |", "",
              "Impas ini bukan SLA atau izin terlambat; hanya biaya operasional kapal dan diesel oil pelabuhan bertambah, asumsi lain tetap. "
              "Bukan ukuran kerugian maksimum, kebutuhan dana awal atau risiko kredit."]
    lines += cost_change_lines(report)
    return lines


def risk_lines(report: dict[str, Any]) -> list[str]:
    lines = ["## 3. Risiko (Risk)", ""]
    if not emphasize_economics(report["recommendation"]):
        return lines + ["Keputusan utama adalah tidak melanjutkan penawaran/rencana yang gagal pemeriksaan. "
                        "Dampak BBM dan delay tersedia sebagai perhitungan pendukung, bukan alasan untuk mengabaikan kegagalan tersebut."]
    lines += ["| Kondisi | Hasil neto PILOG USD | Perubahan dari baseline USD | Dampak |", "|---|---:|---:|---|"]
    for row in report["scenarios"]:
        lines.append(f"| {clean(row['label'])} | {amount(row['economics']['contribution_usd'])} | "
                     f"{amount(row['change_from_baseline_usd'])} | {clean(row['interpretation'])} |")
    meaning = ("Skenario rugi tidak membatalkan GO baseline secara otomatis. " if report["recommendation"]["action"] == "GO"
               else "Baseline sudah rugi; skenario tambahan menunjukkan dampak perubahan biaya, bukan alasan mengubah NO GO menjadi GO. ")
    lines += ["", meaning + "Jika menjadi rencana dasar, hitung ulang dengan freight tetap. "
              "Tidak diasumsikan ada kompensasi atau hedge; skenario bukan probabilitas/worst-case."]
    if len(report["scenarios"]) == 1:
        lines += ["Tidak ada skenario stress tambahan; baseline bukan bukti risiko nol."]
    return lines


def logistics_lines(report: dict[str, Any]) -> list[str]:
    case, base, rec = report["case"], report["baseline"], report["recommendation"]
    lines = ["## 4. Dampak logistik (Logistics impact)", "",
             f"**{clean(case['loading_port'])} → {clean(case['discharging_port'])}; satu arah bermuatan, tanpa biaya balik.**",
             f"Estimasi {amount(base['total_days'])} hari: laut {amount(base['sea_days'])}, muat {amount(base['loading_days'])}, "
             f"bongkar {amount(base['discharge_days'])}, waiting {amount(base['waiting_days'])}.",
             f"Cargo {amount(case['cargo_mt'])} MT; DWT {amount(case['dwt_mt'])} MT."]
    if rec["gate_a"] == "PASS" and not rec["vessel_screen"]["passed"]:
        lines += ["**Screen kapal gagal.** Hasil freight positif tidak membuat kapal lolos."]
    lines += ["Cek DWT hanya kapasitas awal. Kesiapan kapal aktual, DWCC, terminal dan jadwal/laycan belum terbukti dari input; "
              "screen DWT tidak menetapkan kesiapan berlayar."]
    return lines


def tender_lines(report: dict[str, Any]) -> list[str]:
    tender, pricing = report["tender"], report["pricing"]
    mode = "Freight tetap" if pricing["rate_mode"] == "fixed_simulation" else "Indikasi model — belum disimpan sebagai harga tetap"
    lines = ["## 5. Konsekuensi harga (Pricing consequences)", "",
             f"Indeks **{amount(report['index']['index_usd_mt'])}**; OE/HPS barang PI **{amount(report['oe_hps_usd_mt'])}**; "
             f"alpha minimum internal **{amount(report['metrics']['minimum_alpha_usd_mt'])} USD/MT**.",
             f"**{mode}: {amount(pricing['freight_tender_usd_mt'])} USD/MT**, terlihat oleh buyer.",
             "FOB = indeks + alpha; CFR = FOB + freight. Gap = FOB − OE/HPS, bukan CFR − OE/HPS dan bukan laba PI. "
             "Buyer menawar alpha, bukan mengubah freight secara otomatis.",
             "Bid terakhir setiap buyer pada cutoff; harga/gap dalam USD/MT:", "",
             "| Peringkat | Buyer / bid / putaran | Alpha | FOB PI | Freight PILOG | CFR | Gap internal | Hasil |",
             "|---:|---|---:|---:|---:|---:|---:|---|"]
    ids = set(tender["candidate_bid_ids"])
    for row in tender["latest_bids"]:
        status = row["reason"]
        if row["bid_id"] in ids:
            status += "; kandidat"
        if row["bid_id"] == tender["pi_selected_bid_id"]:
            status += "; pilihan PI"
        lines.append(f"| {row['eligible_rank'] if row['eligible_rank'] is not None else '—'} | "
                     f"{clean(row['buyer_id'])} / {clean(row['bid_id'])} / {row['round']} | {amount(row['alpha_usd_mt'])} | "
                     f"{amount(row['fob_usd_mt'])} | {amount(row['freight_usd_mt'])} | {amount(row['cfr_usd_mt'])} | "
                     f"{amount(row['oe_gap_usd_mt'])} | {clean(status)} |")
    if not tender["latest_bids"]:
        lines.append("| — | Tidak ada bid pada cutoff | — | — | — | — | — | Tidak ada kandidat |")
    lines += ["", f"Ranking bukan award; bid lama tidak hidup kembali. Pilihan PI: {clean(tender['pi_selected_bid_id'] or 'Belum diberikan')}."]
    if len(tender["top_tied_bid_ids"]) > 1:
        lines += ["Peringkat tertinggi seri: " + clean(", ".join(tender["top_tied_bid_ids"])) + "; PI memutuskan."]
    financials, ref = report.get("commercial_financials"), price_reference(report)
    if financials is not None and ref is not None:
        value = next(row for row in financials["bid_amounts"] if row["bid_id"] == ref["bid_id"])
        lines += [f"Nilai penawaran CFR {clean(ref['bid_id'])}: **{amount(value['buyer_cfr_offer_value_usd'])} USD** "
                  "= nilai barang PI + freight PILOG, bukan tambahan pendapatan di atas keduanya."]
    if report.get("route_distance"):
        distance = report["route_distance"]
        lines += [f"Jarak satu arah: {amount(distance['value'])} NM, sumber {clean(distance['source_reference'])}. "
                  "OD digunakan hanya untuk jarak; freight dihitung oleh model voyage."]
    else:
        od = report["od_comparison"]
        lines += [f"Freight sistem {amount(report['baseline']['freight_usd_mt'])} versus OD "
                  f"{amount(od['rate_usd_mt']) if od.get('rate_usd_mt') is not None else 'tidak tersedia'} USD/MT. "
                  "Tarif OD berlaku satu arah, tetapi biaya internalnya termasuk balik; selisih bukan margin/penghematan dan OD bukan gate."]
    return lines


def commercial_brief(report: dict[str, Any]) -> str:
    rec = report["recommendation"]
    lines = [f"# {rec['action']} — Keputusan CFR {clean(report['case_id'])}", "",
             "**INTERNAL PI/PILOG — bukan materi buyer.** OE/HPS, gap, bid buyer lain dan ekonomi internal tidak untuk dibagikan kepada buyer.",
             "Rekomendasi sistem, **bukan award** tender atau instruksi pelaksanaan otomatis.", "",
             "## 1. Keputusan komersial (Commercial decision)", ""]
    if "baseline" not in report:
        lines += [clean(rec["summary"]), "Perhitungan belum dapat diselesaikan; tidak ada kandidat/angka pengganti nol.", ""]
        lines += check_lines(rec) + [""] + action_lines(rec)
        lines += ["", "## 2. Eksposur ekonomi (Exposure)", "", "Tidak dapat dihitung dari input yang bermasalah.",
                  "", "## 3. Risiko (Risk)", "", "Dampak finansial belum dihitung; bukan risiko nol.",
                  "", "## 4. Dampak logistik (Logistics impact)", "", "Kelayakan operasi tidak dinyatakan lolos.",
                  "", "## 5. Konsekuensi harga (Pricing consequences)", "", "Tidak ada harga atau pendapatan pengganti nol."]
    else:
        case = report["case"]
        lines += [f"**{clean(case['cargo_description'])}; {amount(case['cargo_mt'])} MT; "
                  f"{clean(case['loading_port'])} → {clean(case['discharging_port'])}; {clean(case['vessel_class'])}, milik.**", ""]
        headline = executive_decision_lines(report) if report.get("commercial_review") else decision_headline(report)
        lines += headline + [""] + financial_lines(report) + [""] + check_lines(rec) + [""] + action_lines(rec)
        lines += [""] + exposure_lines(report) + [""] + risk_lines(report) + [""] + logistics_lines(report) + [""] + tender_lines(report)
        lines += pricing_bridge_lines(report) if report.get("commercial_review") else price_time_lines(report)
    lines += ["", "---", "",
              "Basis estimasi: biaya historis/asumsi dan profil benchmark; bukan realisasi atau quotation pasar terkini. "
              "Persetujuan manusia belum tercatat; penetapan pemenang dan komitmen komersial tetap pada PI/PILOG.",
              "[Rincian perhitungan dan sumber](calculation_audit.md).", ""]
    lines += identity_lines(report)
    return "\n".join(lines) + "\n"


def calculation_audit(report: dict[str, Any]) -> str:
    report = {key: value for key, value in report.items() if not key.startswith("_")}
    lines = [f"# Audit kalkulasi — {clean(report['case_id'])}", "",
             "**INTERNAL PI/PILOG — bukan untuk buyer; memuat OE/HPS dan ekonomi internal.**",
             "Simulasi; semua aritmetika berasal dari fungsi Python Decimal.", "",
             "## Data dan versi", "", f"Formula/rule: {report['version']}; brief: {report['report_version']}; metrics: {report['metrics_version']}.", "",
             "## Kontrak hitungan", "",
             "Hari laut = NM / (knot × 24); hari pelabuhan = Q/rate + waiting/delay.",
             "Biaya = bunker + port/other sekali + running × hari. " + ("OD hanya sumber jarak NM." if report.get("route_distance") else "Tarif OD bukan biaya tambahan."),
             "Target TCE net voyage/komisi sebelum running: freight = (voyage expenses + target TCE × hari) / (Q × (1 − komisi)).",
             "Freight ceil 4 desimal USD/MT; running dikurangkan pada kontribusi, bukan hire tambahan.",
             "Kontribusi = revenue − komisi − bunker − port/other − running.",
             "Ringkasan finansial: pendapatan barang PI = FOB × Q; pendapatan freight PILOG = freight × Q; nilai penawaran buyer = CFR × Q.",
             "Hasil neto PILOG setelah biaya voyage/komisi = contribution_usd, bukan net_revenue_usd (baru setelah komisi). Neto barang PI tidak dimodelkan; OE/HPS bukan HPP.",
             "FOB = indeks + alpha; CFR = FOB + freight; gap internal = FOB − OE/HPS; alpha minimum = OE/HPS − indeks.",
             "Freight impas = cash cost sebelum komisi / [Q × (1 − fraksi komisi)].",
             "Incremental port day = biaya operasional kapal per hari + konsumsi diesel oil pelabuhan per hari × harga diesel oil.",
             "Delay impas tambahan = kontribusi baseline / incremental port day, hanya jika baseline positif dan biaya tambahan > 0.",
             "Metrik bukan gate/SLA. Baseline nol/negatif dan denominator nol ditangani eksplisit.", ""]
    lines += identity_lines(report) + [""]
    if "baseline" in report:
        lines += price_time_lines(report) + [""]
        p = report["pricing"]
        lines += ["## Asal freight dan metrik internal", "",
                  f"Mode tarif: {clean(p['rate_mode'])}; freight dipakai: {clean(p['freight_tender_usd_mt'])} USD/MT.",
                  f"Indikasi model saat evaluasi: {clean(p['computed_freight_usd_mt'])} USD/MT; tidak mengganti harga tetap.",
                  "Fixed simulation bukan approval komersial. Snapshot lama tanpa fixed record tetap jalur indikasi.", "",
                  "| Metrik | Nilai |", "|---|---:|"]
        lines += [f"| {clean(k)} | {clean(v)} |" for k, v in report["metrics"].items()]
        lines += ["", "## Hari dan ekonomi per skenario", "", "| Skenario / variabel | Nilai |", "|---|---:|"]
        for r in report["scenarios"]:
            for key, value in r["economics"].items():
                lines.append(f"| {clean(r['scenario_id'])} / {key} | {clean(value)} |")
        lines += ["", "## Seluruh bid — harga USD/MT; OE/HPS dan gap khusus internal", "",
                  "| Bid | Buyer | Round | Alpha | FOB | Freight terlihat buyer | CFR | Gap FOB−OE/HPS (internal) | Aktif | Eligible | Alasan |",
                  "|---|---|---:|---:|---:|---:|---:|---:|---|---|---|"]
        for r in report["tender"]["bids"]:
            lines.append(f"| {clean(r['bid_id'])} | {clean(r['buyer_id'])} | {r['round']} | {r['alpha_usd_mt']} | {r['fob_usd_mt']} | {r['freight_usd_mt']} | {r['cfr_usd_mt']} | {r['oe_gap_usd_mt']} | {r['is_active_at_cutoff']} | {r['eligible']} | {clean(r['reason'])} |")
    lines += ["", "## Catatan sumber dan asumsi", ""] + [f"- {clean(n)}" for n in report.get("notes", [])]
    lines += ["", "## Hasil lengkap dan lineage (internal)", "", "Angka detail bukan kalkulasi ulang renderer.", "",
              "~~~json", json.dumps(report, ensure_ascii=False, indent=2), "~~~", ""]
    return "\n".join(lines)
