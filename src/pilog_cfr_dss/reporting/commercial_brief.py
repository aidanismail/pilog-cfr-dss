"""Presentation only: every amount and action comes from engine/rules."""
from pilog_cfr_dss.reporting.formatting import number_text as n, price_time
from pilog_cfr_dss.models.freight_desk import COMMODITIES

def clean(value):
    return str(value).replace("|", "/").replace("\r", " ").replace("\n", " ")

STATUS = {"PASS": "Lolos", "FAIL": "Tidak lolos", "NOT_MODELLED": "Belum dimodelkan",
          "ESTIMATED_PASS": "Lolos pendekatan TPC", "PARTIAL_ESTIMATE": "Batas satu port saja"}
CHECK = {"WEIGHT": "Berat", "VOLUME": "Ruang palka", "DRAFT": "Draft"}


def commercial_brief(result):
    case, rec = result["case"], result["recommendation"]
    load, discharge = case["ports"]["load"], case["ports"]["discharge"]
    candidates = [result["classes"][name]["nominal"] for name in rec["selected"]]
    lines = ["# Commercial Brief — PILOG", "",
        f"{clean(load['name'])} → {clean(discharge['name'])} · {COMMODITIES[case['commodity']]} · {n(case['cargo_mt'])} MT",
        "", f"Dihitung {price_time(result['calculated_at'])} · Kasus {clean(result['case_id'])} · Formula {result['formula_version']}", "",
        "## 1. Rekomendasi komersial", "", rec["action"], "",
        "| Kapal | Hari | Total biaya USD | Freight biaya USD/MT | Minimum penawaran USD/MT |",
        "|---|---:|---:|---:|---:|"]
    for name, scenarios in result["classes"].items():
        row = scenarios["nominal"]
        if row["feasible"]:
            lines.append(f"| {name} | {n(row['days'])} | {n(row['total_usd'])} | {n(row['freight_usd_mt'])} | {n(row['minimum_offer_usd_mt'])} |")
        else:
            lines.append(f"| {name} | — | — | Tidak dapat dipakai pada muatan ini | — |")
    lines += ["", "| Kapal | Pemeriksaan | Status | Batas MT |", "|---|---|---|---:|"]
    for name, scenarios in result["classes"].items():
        row = scenarios["nominal"]
        for check in row.get("capacity", {}).get("checks", []):
            lines.append(f"| {name} | {CHECK[check['code']]} | {STATUS[check['status']]} | {n(check.get('limit_mt'))} |")
        if row.get("error"):
            lines.append(f"| {name} | Input | {clean(row['error'])} | — |")
        maximum = scenarios["maximum"]
        lines.append(f"| {name} | Muatan maksimum tolerance | {'Lolos' if maximum['feasible'] else 'Tidak seluruh rentang terlayani'} | {n(maximum.get('capacity', {}).get('limit_mt'))} |")
    lines += ["", "## 2. Exposure", "",
              "| Kapal terpilih | Hire USD | Bunker USD | Port DA USD | Biaya lain USD | Total USD |",
              "|---|---:|---:|---:|---:|---:|"]
    for row in candidates:
        lines.append(f"| {row['vessel_class']} | {n(row['hire_usd'])} | {n(row['bunker_usd'])} | {n(row['port_da_usd'])} | {n(row['other_usd'])} | {n(row['total_usd'])} |")
    if not candidates:
        lines.append("Tidak ada kapal yang memenuhi pemeriksaan awal untuk muatan nominal. Ubah muatan atau profil kapal sebelum menyiapkan penawaran.")
    lines += ["", "## 3. Risiko dan tindakan", ""]
    for row in candidates:
        cap = row["capacity"]
        lines.append(f"- {row['vessel_class']}: batas muatan terhitung {n(cap['limit_mt'])} MT; pembatas {CHECK[cap['binding']]}.")
        if not result["classes"][row["vessel_class"]]["maximum"]["feasible"]:
            lines.append("  Batasi jumlah muatan yang ditawarkan atau gunakan kelas kapal yang memenuhi batas atas toleransi.")
        if cap["checks"][2]["status"] == "NOT_MODELLED":
            lines.append("  Lengkapi batas draft kedua pelabuhan sebelum menetapkan jumlah muatan.")
        else:
            lines.append("  Konfirmasikan jumlah muatan dengan data kapal dan terminal; pemeriksaan TPC masih berupa perkiraan.")
        if row["commercial"] and row["commercial"]["surplus_usd"] < 0:
            lines.append(f"  Tarif jual di bawah biaya. Naikkan minimal {n(row['commercial']['rate_change_to_break_even'])} USD/MT sampai {n(row['minimum_offer_usd_mt'])} USD/MT, atau ubah biaya/operasi.")
    lines += ["- Seri harga bunker pada bagian sumber adalah pembanding. Periksa jenis bahan bakar dan lokasi pembelian; harga manual mengikuti input kasus.",
        "- Terms digunakan untuk estimasi waktu operasi. Klaim demurrage/despatch tidak termasuk.", "",
        "## 4. Dampak logistik", "",
        "| Kapal | Quantity | Cargo MT | Hari voyage | Freight biaya USD/MT | Hasil |",
        "|---|---|---:|---:|---:|---|"]
    labels = {"minimum": "Minimum", "nominal": "Nominal", "maximum": "Maksimum"}
    for name, scenarios in result["classes"].items():
        for key, row in scenarios.items():
            lines.append(f"| {name} | {labels[key]} | {n(row['cargo_mt'])} | {n(row.get('days'))} | {n(row.get('freight_usd_mt'))} | {'Dapat dihitung' if row['feasible'] else clean(row.get('error', 'Kapasitas tidak cukup'))} |")
    mode_name = {"factor": "faktor terms", "calendar": "kalender operasi"}
    lines += ["", f"Terms muat: {load['terms']} ({mode_name[load['time_basis']]}); terms bongkar: {discharge['terms']} ({mode_name[discharge['time_basis']]}).",
        "Ketersediaan kapal dan slot terminal tidak ditentukan oleh hasil biaya.", "",
        "## 5. Konsekuensi harga", ""]
    if case.get("selling_freight_usd_mt") is None:
        lines.append("Gunakan minimum penawaran pada bagian 1 sebagai batas penutup biaya yang dimodelkan. Tarif jual belum diisi; pendapatan, surplus dan TCE komersial belum dihitung.")
    else:
        lines += ["| Kapal | Tarif jual USD/MT | Pendapatan freight USD | Biaya voyage USD | Hire USD | Surplus/defisit USD | TCE USD/hari |",
                  "|---|---:|---:|---:|---:|---:|---:|"]
        for name, rows in result["classes"].items():
            row = rows["nominal"]
            if row["feasible"]:
                co = row["commercial"]
                lines.append(f"| {name} | {n(co['selling_freight_usd_mt'])} | {n(co['net_freight_revenue_usd'])} | {n(row['voyage_expenses_usd'])} | {n(row['hire_usd'])} | {n(co['surplus_usd'])} | {n(co['tce_usd_day'])} |")
    lines += ["", "Komisi 0%. Freight biaya mencakup hire, bunker, Port DA dan biaya lain yang dimasukkan; tanpa margin otomatis. Pendapatan penjualan barang PI tidak dicampur dengan pendapatan freight PILOG.", "",
        "### Sumber dan waktu", "",
        f"Fearnpulse terakhir diambil: {price_time(case['market_snapshot'].get('fetched_at'))}.",
        "| Data | Seri / nilai | Tanggal sumber |", "|---|---|---|"]
    for family, quote in case["market_snapshot"]["tc_rates"].items():
        lines.append(f"| TC Rates {family} | {n(quote['value'])} USD/hari; {clean(quote['series'])} | {quote.get('source_observed_on', '—')} |")
    for grade, item in case["fuel"].items():
        manual = case['sources'].get('fuel.' + grade + '.value', {}).get('status') == 'manual_override'
        label = 'input manual' if manual else 'harga pembanding'
        series = "seri pembanding sebelumnya" if manual else "seri pembanding"
        observed = "—" if manual else item.get('source_observed_on', '—')
        lines.append(f"| {grade}, {label} | {n(item['value'])} USD/MT; {series}: {clean(item['series'])} | {observed} |")
    sources = {(x["publisher"], x["source_file"], x["observation_date"]) for x in case.get("report_snapshot", {}).get("records", []) if x["product"] == case["commodity"]}
    for publisher, file, date in sorted(sources):
        lines.append(f"| {publisher}, konteks harga barang | {clean(file)} | {date} |")
    lines += ["", f"Jarak: {n(case['distance_nm'])} NM; {clean(case['sources'].get('distance_nm', {}).get('source_reference', 'Input manual'))}.",
        f"Spesifikasi: {clean(case['profile_source']['source_url'])}, versi {clean(case['profile_source']['document_version'])}; nilai tambahan dan perubahan manual tersedia dalam paket kasus.",
        f"ID data input (SHA-256): {result['input_sha256']}. Rincian angka, perubahan manual, dan sumber tersimpan dalam paket kasus.", "",
        "Rekomendasi untuk persiapan penawaran; keputusan dan pelaksanaan tetap pada pihak berwenang.", ""]
    return "\n".join(lines)
