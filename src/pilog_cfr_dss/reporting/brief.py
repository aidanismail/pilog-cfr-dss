from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any


def _shown(value: Any, unit: str = "") -> str:
    if value is None:
        return "belum tersedia"
    try:
        number = Decimal(str(value))
        result = format(number, ",.4f")
    except (InvalidOperation, ValueError):
        result = str(value)
    return f"{result} {unit}".strip()


def render_brief(report: dict[str, Any]) -> str:
    """Present executed results; this module performs no business arithmetic."""
    pricing = report["pricing"]
    quantity = report["quantity_basis"]
    recommendation = report["recommendation"]
    economics = report.get("scenario_economics", {}).get("CFR-PILOG", {})
    lines = [
        "# Decision Brief — Simulation Iteration 2 Revision", "",
        f"- Case ID: `{report['case_id']}`",
        f"- Tahap: `{report.get('decision_stage')}`; respons buyer: `{report.get('buyer_response')}`",
        f"- Mode: `{report['mode']}` / `{report['status']}`",
        f"- Gate 1: **{report['gate_1']['outcome']}**",
        f"- Gate 2: **{report['gate_2']['outcome']}**",
        f"- Rekomendasi: **{recommendation['action']}**",
        "- Approval: **PENDING_HUMAN_REVIEW** — sistem tidak mengirim quote atau melakukan fixture.", "",
        "## Mengapa dan apa berikutnya", "",
    ]
    lines.extend(f"- `{reason}`" for reason in recommendation["reasons"])
    lines.extend(["", f"**Langkah berikutnya:** {recommendation['next_action']}", ""])
    lines.extend([
        "## Konteks transaksi dan basis angka", "",
        f"- Seller komoditas: {report['contracting_roles']['commodity_seller']}; penyedia jasa freight: {report['contracting_roles']['freight_provider']}.",
        f"- Rute: {report['route']['origin']} → {report['route']['destination']}.",
        f"- Cargo/DWCC tunggal: **{_shown(quantity['cargo_mt'], 'MT')}** untuk waktu pelabuhan, screen DWT, freight revenue, komisi, dan biaya per MT.",
        "- Angka 46.000 MT dari input Aqaba lama tidak dipakai dan tidak ada voyage expense allocation quantity dalam kontrak simulasi ini.",
        "",
        "## Harga komoditas dan indikasi CFR", "",
        f"- Index: {_shown(pricing['index_usd_mt'], 'USD/MT')}; Alpha: {_shown(pricing['alpha_usd_mt'], 'USD/MT')}.",
        f"- FOB baseline = Index + Alpha: **{_shown(pricing['fob_usd_mt'], 'USD/MT')}**.",
        f"- Tarif jual freight PILOG: {_shown(economics.get('freight_selling_rate_usd_mt'), 'USD/MT')}.",
        f"- CFR adjustment: {_shown(pricing.get('adjustment_usd_mt'), 'USD/MT')}.",
        f"- CFR indikatif: **{_shown(pricing['cfr_indicative_usd_mt'], 'USD/MT')}**.",
        "- Harga FOB bukan profit barang PI Group. CFR indikatif belum diuji terhadap willingness-to-pay buyer atau margin komoditas seller.",
        "",
        "## Screen kelas kapal — DWT saja", "",
        f"- Versi kebijakan: `{report['vessel_policy_version']}`.",
    ])
    for name, item in report.get("vessel_class_screen", {}).items():
        lines.append(
            f"- {name}: rentang {_shown(item['class_min_dwt_mt'], 'MT')}–{_shown(item['class_max_dwt_mt'], 'MT')}; "
            f"DWT kapal kasus {_shown(item['case_vessel_dwt_mt'], 'MT')}; cargo {_shown(item['cargo_mt'], 'MT')}; "
            f"hasil `{'PASS' if item['screen_pass'] else 'FAIL'}` (`{item['reason']}`)."
        )
    lines.extend([
        f"- Kandidat kelas dalam CFR: **{report['vessel_class_selection'].get('preliminary_candidate_class') or 'belum ada'}**.",
        "- PASS DWT belum membuktikan DWCC aktual, draft, batas terminal, laycan, atau ketersediaan kapal.", "",
        "## Perhitungan fisik — hasil Python", "",
    ])
    trace = report["calculation_trace"]
    if trace.get("results"):
        for name, item in trace["results"].items():
            lines.append(f"- {name}: **{_shown(item['value'], item['unit'])}** — `{item['formula']}`.")
    else:
        lines.append("- Belum dihitung karena input kritis terblokir.")
    lines.extend(["", "## Ekonomi jasa freight PILOG — hasil Python", ""])
    if economics.get("status") == "CALCULATED":
        labels = (
            ("cargo_mt", "Basis cargo", "MT"),
            ("total_voyage_days", "Total hari voyage", "hari"),
            ("owned_running_cost_usd", "Running cost kapal milik", "USD"),
            ("fuel_oil_cost_usd", "Fuel oil cost", "USD"),
            ("diesel_cost_usd", "Diesel cost", "USD"),
            ("bunker_cost_usd", "Total bunker", "USD"),
            ("port_and_other_cost_usd", "Port/other aggregate", "USD"),
            ("total_freight_cost_usd", "Total freight cost", "USD"),
            ("freight_cost_per_mt_usd", "Freight cost per MT", "USD/MT"),
            ("freight_selling_rate_usd_mt", "Tarif jual freight", "USD/MT"),
            ("gross_freight_revenue_usd", "Gross freight revenue", "USD"),
        )
        for key, label, unit in labels:
            lines.append(f"- {label}: **{_shown(economics[key], unit)}**.")
        for key, value in economics["commission_components_usd"].items():
            lines.append(f"- Komisi {key}: {_shown(value, 'USD')}.")
        lines.extend([
            f"- Total komisi: **{_shown(economics['commission_usd'], 'USD')}**.",
            f"- Kontribusi freight PILOG: **{_shown(economics['net_freight_contribution_usd'], 'USD')}**.",
            "- Kontribusi ini bukan laba bersih PILOG atau margin barang PI Group; minimum margin komersial belum ditetapkan.",
            "",
            "### Rumus yang dieksekusi", "",
        ])
        lines.extend(f"- {name}: `{formula}`." for name, formula in economics["formulae"].items())
    else:
        lines.append(f"- Tidak dapat dihitung: `{economics.get('status', 'NOT_CALCULATED')}`; alasan: {', '.join(economics.get('reasons', [])) or 'lihat Gate dan quality'}.")
    lines.extend(["", "## Perbandingan alternatif komersial", ""])
    for item in report["gate_2"].get("scenario_results", []):
        lines.append(f"- `{item['scenario_id']}`: **{item['outcome']}**; alasan: {', '.join(item['reasons'])}.")
    lines.extend([
        "- FOB adalah baseline harga; profitabilitas PI seller belum tersedia. Kapal adalah sub-keputusan CFR, bukan skenario komersial tambahan.",
        "",
        "## Mutu data dan batas kepercayaan", "",
        f"- Status quality: `{report['quality']['status']}`.",
    ])
    for item in report["quality"]["checks"]:
        if item["status"] != "PASS":
            lines.append(f"- `{item['code']}`: {item['status']}; field: {', '.join(item['fields'])}; {item['detail']}.")
    lines.extend(f"- {item}" for item in trace.get("limitations", []))
    lines.extend(f"- Asumsi: {item}" for item in report.get("simulation_assumptions", []))
    lines.extend(f"- Belum diputuskan: `{item}`." for item in report.get("unresolved_definitions", []))
    lines.extend([
        "", "## Jejak run", "",
        f"- Dataset SHA-256: `{report['dataset_sha256']}`.",
        f"- Catalog SHA-256: `{report['catalog_sha256']}`.",
        f"- Manual input SHA-256: `{report['manual_sha256']}`.",
        f"- Vessel policy SHA-256: `{report['vessel_policy_sha256']}`.",
        f"- Formula version: `{report['formula_version']}`; rule version: `{report['rule_version']}`.",
    ])
    if report.get("input_snapshot"):
        lines.extend(f"- Snapshot {name}: `{item['file']}`." for name, item in report["input_snapshot"].items())
    lines.extend(["", "Hasil ini simulasi untuk review mentor/atasan; bukan quote, approval, fixture, atau transaksi otomatis.", ""])
    return "\n".join(lines)
