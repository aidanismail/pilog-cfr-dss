"""Stakeholder-first I3 decision brief; calculations are never performed here."""

from __future__ import annotations

from decimal import Decimal
from typing import Any


def _display(value: str | None, places: int = 2) -> str:
    if value is None:
        return "—"
    return f"{Decimal(value):,.{places}f}"


def render_i3_brief(report: dict[str, Any]) -> str:
    recommendation = report["recommendation"]
    action = recommendation["action"]
    action_label = "NO GO" if action == "NO_GO" else "GO"
    lines = [
        f"# Decision brief Iterasi 3 — {report['case_id']}", "",
        f"## Rekomendasi: {action_label} CFR — simulasi, hanya untuk review", "",
        f"**Alasan utama:** `{recommendation['reason_category']}` — {', '.join(recommendation['reason_codes'])}.",
        f"**Tindakan berikutnya:** {recommendation['next_action']}",
        "**Kewenangan:** keputusan final tetap pada pejabat PI/PILOG; tidak ada award, quotation, approval, atau fixture otomatis.", "",
    ]
    if recommendation["reason_category"] == "DATA_ISSUE":
        lines += [
            "NO GO ini berarti **belum aman memberi rekomendasi GO karena input/perhitungan tidak sah**, "
            "bukan bukti bahwa buyer atau harga gagal secara komersial.", "",
            "## Audit", "",
            f"- Versi formula/rule: `{report['formula_version']}` / `{report['rule_version']}`.",
            "- Mode: `simulation`; status: `advisory-only`.",
        ]
        return "\n".join(lines) + "\n"

    tender, economics, gates = report["tender"], report["economics"], report["gates"]
    selected = report["selected_bid"]
    lines += [
        "## Apa yang dinilai", "",
        f"- Barang/rute: {report['commodity']}; {report['route']['origin']} → {report['route']['destination']}; "
        f"{_display(report['cargo_mt'], 0)} MT.",
        f"- Basis indeks **sintetis**: Argus midpoint {_display(tender['index']['argus_midpoint_usd_mt'])} + "
        f"Fertecon midpoint {_display(tender['index']['fertecon_midpoint_usd_mt'])}, "
        f"dibagi 2 = **{_display(tender['index']['index_usd_mt'])} USD/MT**.",
        f"- OE/HPS PI **sintetis**: {_display(tender['oe_hps_usd_mt'])} USD/MT; ini bukan HPP/COGS.",
        f"- Kandidat pilihan PI dalam fixture: **{selected['bid_id'] if selected else 'tidak ada'}**; "
        "DSS tidak memilih pemenang tender.", "",
        "## Jejak putaran tender", "",
        "| Putaran | Buyer sintetis | Alpha USD/MT | FOB USD/MT | FOB − OE/HPS | Lolos floor? | CFR indikatif USD/MT |",
        "|---:|---|---:|---:|---:|---|---:|",
    ]
    for bid in tender["bids"]:
        lines.append(
            f"| {bid['round']} | {bid['buyer_id']} | {_display(bid['alpha_usd_mt'])} | "
            f"{_display(bid['fob_usd_mt'])} | {_display(bid['oe_gap_usd_mt'])} | "
            f"{'Ya' if bid['eligible_oe_floor'] else 'Tidak'} | {_display(bid['cfr_usd_mt'])} |"
        )
    lines += [
        "", "Harga FOB = indeks + alpha buyer **sekali**. `FOB − OE/HPS ≥ 0` adalah ambang tender, "
        "**bukan laba akuntansi PI**. CFR indikatif = FOB + biaya freight OD **proxy**; "
        "angka CFR pada bid yang gagal floor hanya jejak hitung, bukan penawaran yang boleh diteruskan.", "",
        "## Ekonomi freight PILOG — kapal milik, asumsi simulasi", "",
        "| Komponen | Nilai |",
        "|---|---:|",
        f"| Hari voyage | {_display(economics['total_voyage_days'])} hari |",
        f"| Running kapal milik | USD {_display(economics['owned_running_usd'])} |",
        f"| Fuel oil + diesel/bunker | USD {_display(economics['bunker_usd'])} |",
        f"| Port dan other voyage costs (agregat) | USD {_display(economics['port_and_other_usd'])} |",
        f"| **Total biaya voyage** | **USD {_display(economics['total_voyage_cost_usd'])}** |",
        f"| Proxy biaya OD = total biaya / 45.000 MT | **{_display(economics['derived_od_cost_proxy_usd_mt'], 4)} USD/MT** |",
        f"| Tarif jual jasa freight PILOG dari dataset I2 | {_display(economics['freight_selling_rate_pilog_usd_mt'])} USD/MT |",
        f"| Revenue freight PILOG = tarif jual × 45.000 MT | USD {_display(economics['pilog_freight_revenue_usd'])} |",
        f"| Komisi (asumsi basis gross revenue) | USD {_display(economics['commission_usd'])} |",
        f"| **Kontribusi PILOG = revenue − komisi − biaya** | **USD {_display(economics['pilog_freight_contribution_usd'])}** |",
        "", "**Jangan jumlahkan proxy OD dengan total biaya voyage:** keduanya menggambarkan biaya yang sama "
        "dalam satuan berbeda. Tarif jual PILOG bukan komponen freight OD pada harga CFR buyer; "
        "selisih keduanya belum menjelaskan alokasi komersial PI–PILOG.", "",
        "## Hasil Gate dan tindakan", "",
        f"- Gate A — kandidat pasca-tender dan batas OE/HPS: **{gates['gate_a']}**.",
        f"- Gate B — screen kapal awal dan kontribusi freight PILOG ≥ 0: **{gates['gate_b']}**.",
    ]
    if gates.get("selected_vessel_class"):
        lines.append(f"- Kelas kapal yang lolos screen awal: **{gates['selected_vessel_class']}**; "
                     "ini belum membuktikan DWCC aktual, draft, terminal, atau availability.")
    if action == "NO_GO" and gates["gate_b"] == "NOT_EVALUATED":
        lines.append("- Gate B tidak dipakai untuk menerima bid ketika Gate A gagal; ekonomi freight di atas hanya diagnostik.")
    lines += ["", "## Batas kepercayaan sebelum keputusan nyata", ""]
    lines.extend(f"- {item}" for item in report["limitations"])
    lines += [
        "", "## Audit", "",
        f"- Versi formula/rule: `{report['formula_version']}` / `{report['rule_version']}`.",
        f"- SHA-256 dataset: `{report['dataset_sha256']}`.",
        f"- SHA-256 fixture tender: `{report['case_fixture_sha256']}`.",
        "- Semua input dan label sumber ada di `decision_brief.json` serta `input_snapshot/` pada folder run.",
        "- Status persetujuan manusia: `PENDING_HUMAN_REVIEW`.",
    ]
    return "\n".join(lines) + "\n"
