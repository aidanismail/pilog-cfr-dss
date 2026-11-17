"""White/blue freight desk. No business calculations or tender imports."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from pilog_cfr_dss.application.freight_desk import (
    default_case, digest, evaluate, export_case, import_case, matrix, override,
    serializable, update_route, select_terms,
)
from pilog_cfr_dss.models.freight_desk import COMMODITIES, TERMS
from pilog_cfr_dss.reporting.commercial_brief import commercial_brief
from pilog_cfr_dss.reporting.formatting import number_text as fmt, price_time
from pilog_cfr_dss.sources.fearnpulse import fetch_snapshot, latest_saved, save_runtime_snapshot
from pilog_cfr_dss.sources.fertilizer_reports import for_product, read_assessments
from pilog_cfr_dss.sources.route_distance import ports
from pilog_cfr_dss.validation.numbers import timestamp

STYLE = """
<style>
.block-container{max-width:1280px;padding-top:2rem}
h1,h2,h3{color:#142D43;font-weight:650;letter-spacing:-.025em}
h1{font-size:2rem} h2{font-size:1.4rem}
[data-testid="stMetric"]{border:1px solid #DFE7EE;border-radius:6px;padding:12px}
.stButton>button[kind="primary"]{background:#1E70B8;border-color:#1E70B8}
hr{border-color:#DFE7EE}
</style>
"""


@st.cache_data(ttl=60, show_spinner=False)
def fresh_market():
    return fetch_snapshot()


@st.cache_data(show_spinner=False)
def port_catalog(path, version):
    return ports(Path(path))


def get_value(case, path):
    value = case
    for key in path.split("."):
        value = value[key]
    return value


def widget_prefix(case):
    return case["case_id"] + "_" + str(st.session_state.get("widget_generation", 0))


def edit_table(case, entries, key, compact=False):
    rows = []
    for path, label, unit in entries:
        value = get_value(case, path)
        source = case["sources"].get(path, {})
        source_text = ("Input manual" if source.get("status") == "manual_override" else
                       "Fearnpulse (harga pembanding)" if source.get("status") == "market_proxy" else
                       "Estimasi rute laut" if source.get("source_status") == "estimated_sea_route" else
                       "Baltic" if "balticexchange" in source.get("source", "") else
                       "Voyage Estimate" if "Estimate.xlsx" in source.get("source", "") else
                       "Nilai awal")
        rows.append({"Parameter": label, "Nilai": None if value is None else float(value),
                     "Satuan": unit, "Sumber": source_text})
    frame = pd.DataFrame(rows)
    if compact:
        frame = frame.drop(columns=["Sumber"])
    editor_key = widget_prefix(case) + "_" + key
    if key == "shipment":
        editor_key += "_route_" + str(st.session_state.get("route_generation", 0))
    edited = st.data_editor(frame, key=editor_key, hide_index=True,
        width="stretch", disabled=["Parameter", "Satuan", "Sumber"],
        column_config={"Nilai": st.column_config.NumberColumn(min_value=0.0,
                       help="Presisi input dipertahankan; ringkasan hasil dua desimal.")},
        num_rows="fixed")
    for index, (path, _, _) in enumerate(entries):
        value = edited.iloc[index]["Nilai"]
        converted = None if pd.isna(value) else str(value)
        old = get_value(case, path)
        # Compare numeric values rather than "13000" versus "13000.0".
        if (converted is None) != (old is None) or (
                converted is not None and old is not None and str(float(old)) != str(float(converted))):
            override(case, path, converted)


def calendar_editor(case, side):
    port = case["ports"][side]
    prefix = widget_prefix(case) + "_" + side
    with st.expander("Kalender kerja"):
        mode = st.selectbox("Basis waktu", ["factor", "calendar"],
            index=0 if port["time_basis"] == "factor" else 1,
            format_func=lambda x: "Faktor terms" if x == "factor" else "Kalender operasi",
            key=prefix + "_basis")
        override(case, "ports." + side + ".time_basis", mode)
        if mode == "factor":
            st.caption("Faktor estimasi: " + fmt(TERMS[port["terms"]]["factor"]) +
                       ". Sumber: referensi terms CMN.")
            return
        zone = st.text_input("Zona waktu (IANA)", port["calendar"]["timezone"],
                             key=prefix + "_timezone", help="Contoh Asia/Jakarta atau Asia/Kolkata. UTC adalah default perencanaan.")
        override(case, "ports." + side + ".calendar.timezone", zone.strip())
        dates = st.text_area("Tanggal tidak bekerja", "\n".join(port["calendar"].get("holidays", [])),
            key=prefix + "_holidays", help="Satu tanggal YYYY-MM-DD per baris. Daftar diisi pengguna, bukan kalender libur otomatis.")
        override(case, "ports." + side + ".calendar.holidays", [v.strip() for v in dates.splitlines() if v.strip()])
        custom_key = prefix + "_custom_calendar"
        custom = st.checkbox("Ubah jam kerja mingguan", value="windows" in port["calendar"], key=custom_key)
        if custom:
            from pilog_cfr_dss.calculations.port_time import working_windows
            seed = port["calendar"].get("windows") or {str(i): working_windows(port["terms"], i) for i in range(7)}
            raw = st.text_area("Interval kerja per hari", json.dumps(seed), key=prefix + "_windows",
                help='0=Senin … 6=Minggu. Interval dalam menit: [0,1440] berarti satu hari penuh; [] berarti tidak bekerja.')
            try:
                windows = json.loads(raw)
                if not isinstance(windows, dict) or set(windows) != {str(i) for i in range(7)}:
                    raise ValueError()
                if "windows" in port["calendar"]:
                    override(case, "ports." + side + ".calendar.windows", windows)
                else:
                    port["calendar"]["windows"] = windows
            except (ValueError, TypeError):
                st.error("Format interval kalender belum valid.")
                st.session_state["input_errors"].append("Interval kalender belum valid.")
        else:
            port["calendar"].pop("windows", None)
        st.caption("Kalender operasi menggantikan faktor terms. Hari libur yang belum dimasukkan tidak diperhitungkan.")


def port_card(case, root, choices, side, title):
    port = case["ports"][side]
    prefix = widget_prefix(case) + "_" + side
    with st.container(border=True):
        st.subheader(title)
        current = (port["name"], port["country"])
        if current not in choices:
            choices = sorted([*choices, current])
        chosen = st.selectbox("Pelabuhan", choices, index=choices.index(current),
            format_func=lambda x: x[0] + ", " + x[1], key=prefix + "_port")
        if chosen != current:
            override(case, "ports." + side + ".name", chosen[0])
            override(case, "ports." + side + ".country", chosen[1])
            # Never transfer a terminal draft limit to a different port.
            override(case, "ports." + side + ".draft_limit_m", None)
            update_route(case, root)
            st.session_state["route_generation"] = st.session_state.get("route_generation", 0) + 1
            st.rerun()
        terms = st.selectbox("Terms", list(TERMS), index=list(TERMS).index(port["terms"]),
            format_func=lambda x: x + " — " + TERMS[x]["label"], key=prefix + "_terms")
        select_terms(case, side, terms)
        entries = [(f"ports.{side}.rate_mt_day", "Kecepatan muat" if side == "load" else "Kecepatan bongkar", "MT/24 jam kerja"),
            (f"ports.{side}.port_da_usd", "Port DA", "USD"),
            (f"ports.{side}.draft_limit_m", "Batas draft port (opsional)", "m"),
            (f"ports.{side}.waiting_days", "Waktu tunggu", "hari"),
            (f"ports.{side}.allowance_days", "Tambahan waktu operasi", "hari"),
            (f"ports.{side}.time_margin_percent", "Margin waktu pelabuhan", "%")]
        edit_table(case, entries, side, compact=True)
        st.caption("Margin menambah durasi setelah terms/kalender. Periksa agar tidak menghitung hambatan yang sama dua kali.")
        calendar_editor(case, side)


def inputs(case, root):
    st.session_state["input_errors"] = []
    st.header("Input pengiriman")
    a, b, c = st.columns([2, 1, 1])
    with a:
        commodity = st.selectbox("Komoditas", list(COMMODITIES),
            index=list(COMMODITIES).index(case["commodity"]), format_func=COMMODITIES.get,
            key=widget_prefix(case) + "_commodity")
        override(case, "commodity", commodity)
    with b:
        current_start = timestamp(case["start_at"]).astimezone(timezone.utc)
        start_date = st.date_input("Mulai muat (UTC)", current_start.date(),
            key=widget_prefix(case) + "_date", format="DD/MM/YYYY",
            help="Default awal bulan adalah jadwal perencanaan, bukan jadwal aktual.")
    with c:
        start_time = st.time_input("Jam (UTC)", current_start.time().replace(tzinfo=None),
            key=widget_prefix(case) + "_time", step=60)
    start = datetime.combine(start_date, start_time, timezone.utc)
    if start != timestamp(case["start_at"]):
        override(case, "start_at", start.isoformat())
    edit_table(case, [
        ("cargo_mt", "Muatan nominal", "MT"),
        ("stowage_factor_m3_mt", "Stowage factor", "m³/MT"),
        ("tolerance_percent", "Tolerance ±", "%"),
        ("distance_nm", "Jarak laut satu arah", "NM"),
        ("hire_usd_day", "Hire/day", "USD/hari"),
        ("fuel.VLSFO.value", "Harga VLSFO", "USD/MT"),
        ("fuel.LSMGO.value", "Harga LSMGO", "USD/MT"),
        ("bunker_delay_days", "Bunker delay", "hari"),
        ("selling_freight_usd_mt", "Tarif jual freight (opsional)", "USD/MT"),
    ], "shipment")
    choices = port_catalog(str(root / "data/raw/Ports.xlsx"), (root / "data/raw/Ports.xlsx").stat().st_mtime_ns)
    a, b = st.columns(2)
    with a:
        port_card(case, root, choices, "load", "Pelabuhan muat")
    with b:
        port_card(case, root, choices, "discharge", "Pelabuhan bongkar")
    with st.expander("Profil kapal dan biaya lain"):
        st.caption("Supramax memakai benchmark Baltic BSI63, 63.500 DWT. Konsumsi tidak berubah otomatis saat speed diedit.")
        columns = st.columns(2)
        labels = [
            ("dwt_mt", "DWT", "MT"), ("summer_draft_m", "Summer draft", "m"),
            ("grain_m3", "Kapasitas palka grain", "m³"), ("tpc_mt_cm", "TPC", "MT/cm"),
            ("speed_knots", "Kecepatan bermuatan", "knot"),
            ("sea_vlsfo_mt_day", "VLSFO saat berlayar", "MT/hari"),
            ("sea_lsmgo_mt_day", "LSMGO saat berlayar", "MT/hari"),
            ("port_vlsfo_mt_day", "VLSFO di port", "MT/hari"),
            ("port_lsmgo_mt_day", "LSMGO di port", "MT/hari"),
            ("bunkers_allowance_mt", "Allowance bunker", "MT"),
            ("constants_allowance_mt", "Allowance constants", "MT")]
        for column, family in zip(columns, case["profiles"]):
            with column:
                st.subheader(family)
                edit_table(case, [(f"profiles.{family}.{key}", label, unit) for key, label, unit in labels], family)
        st.subheader("Biaya tambahan")
        rows = pd.DataFrame(case["other_costs"], columns=["id", "label", "amount", "unit"])
        edited = st.data_editor(rows, key=widget_prefix(case) + "_other", num_rows="dynamic", hide_index=True,
            column_config={"amount": st.column_config.NumberColumn("Nilai USD", min_value=0.0),
                           "unit": st.column_config.SelectboxColumn(options=["USD"], default="USD")})
        cleaned = []
        for row in edited.to_dict("records"):
            if not row.get("id") and not row.get("label"):
                continue
            cleaned.append({k: str(v) for k, v in row.items()})
        if cleaned != case["other_costs"]:
            override(case, "other_costs", cleaned)


def market_context(case):
    snapshot = case["market_snapshot"]
    st.caption("Fearnpulse terakhir diambil: " + price_time(snapshot.get("fetched_at")))
    with st.expander("Data pasar dan sumber"):
        st.subheader("TC Rates — pembanding")
        st.dataframe(pd.DataFrame([{"Kelas": k, "TC Rates USD/hari": fmt(v["value"]),
            "Seri": v["series"], "Tanggal": v["source_observed_on"]} for k, v in snapshot["tc_rates"].items()]),
            hide_index=True, width="stretch")
        st.caption("Hire/day tetap input sewa terpisah. TC Rates tidak ditambahkan ke freight biaya.")
        st.dataframe(pd.DataFrame([{"Input": grade, "Harga USD/MT": fmt(v["value"]), "Jenis harga pembanding": v["series"],
            "Tanggal seri": v["source_observed_on"], "Sumber nilai": "Input manual" if case["sources"].get("fuel."+grade+".value",{}).get("status")=="manual_override" else v["source_reference"]} for grade, v in case["fuel"].items()]),
            hide_index=True, width="stretch")
        st.caption("Seri Singapore 380 CST dan Singapore MGO tersedia sebagai harga pembanding; jenisnya belum tentu sama dengan grade bahan bakar yang digunakan.")
        st.subheader("Harga barang — " + COMMODITIES[case["commodity"]])
        records = [dict(row, context_scope="Basis dan wilayah asli sumber")
            for row in for_product(case["report_snapshot"], case["commodity"])]
        if records:
            st.dataframe(pd.DataFrame([{"Penerbit": x["publisher"], "Assessment": x["label"], "Basis": x["basis"],
                "Low USD/MT": fmt(x["low"]), "High USD/MT": fmt(x["high"]), "Tanggal": x["observation_date"],
                "Cakupan": x["context_scope"], "Halaman": x["page"], "File": x["source_file"]} for x in records]), hide_index=True, width="stretch")
        else:
            st.warning("Assessment produk belum terbaca; perhitungan biaya tidak memakai harga produk lain.")
        if case["commodity"] == "ammonium_chloride":
            st.caption("Argus: CFR Southeast Asia. Ammonium chloride tidak ditemukan pada laporan Fertecon yang tersedia.")
        st.subheader("Freight pembanding")
        freight = [x for x in case["report_snapshot"]["records"] if x["kind"] == "freight"
            and x["product"] in (case["commodity"], "dry_bulk_fertilizer")]
        if freight:
            st.dataframe(pd.DataFrame([{"Penerbit": x["publisher"], "Rute sumber": x["label"],
                "Cargo sumber (kt)": x["cargo_kt"], "Low USD/MT": fmt(x["low"]), "High USD/MT": fmt(x["high"]),
                "Produk sumber": x["product"], "Tanggal": x["observation_date"], "Halaman": x["page"]} for x in freight]),
                hide_index=True, width="stretch")
            st.caption("Konteks rute/tonase sumber; bukan quote pelabuhan tujuan. Freight pupuk umum bukan assessment khusus ZA/chloride.")
        for error in case["report_snapshot"]["errors"]:
            st.warning(error["source"] + ": " + error["error"])


def results_view(result):
    st.header("Hasil freight")
    st.info(result["recommendation"]["action"])
    for family, scenarios in result["classes"].items():
        nominal = scenarios["nominal"]
        title = family + (" · " + fmt(nominal["freight_usd_mt"]) + " USD/MT" if nominal["feasible"] else " · Muatan atau input perlu diperiksa")
        with st.expander(title, expanded=True):
            if not nominal["feasible"]:
                st.warning(nominal.get("error", "Muatan nominal melebihi kapasitas screening kapal."))
            else:
                a, b, c = st.columns(3)
                a.metric("Total biaya USD", fmt(nominal["total_usd"]))
                b.metric("Hari voyage", fmt(nominal["days"]))
                c.metric("Minimum penawaran USD/MT", fmt(nominal["minimum_offer_usd_mt"]))
                if nominal["commercial"]:
                    a, b, c = st.columns(3)
                    a.metric("Pendapatan freight USD", fmt(nominal["commercial"]["net_freight_revenue_usd"]))
                    b.metric("Surplus/defisit USD", fmt(nominal["commercial"]["surplus_usd"]))
                    c.metric("TCE hasil USD/hari", fmt(nominal["commercial"]["tce_usd_day"]))
                st.dataframe(pd.DataFrame([{"Pelabuhan": label, "Hari dasar": fmt(t["base_days"]),
                    "Hari setelah terms/kalender": fmt(t["terms_days"]), "Margin waktu %": fmt(t["margin_percent"]),
                    "Tambahan margin hari": fmt(t["margin_days"]), "Hari operasi": fmt(t["operation_days"])}
                    for side, label in (("load", "Muat"), ("discharge", "Bongkar"))
                    for t in [nominal["port_times"][side]]]), hide_index=True, width="stretch")
                st.dataframe(pd.DataFrame([{"Aktivitas": x["activity"], "Hari": fmt(x["days"]),
                    "Hire USD": fmt(x["hire_usd"]), "VLSFO MT": fmt(x["vlsfo_mt"]), "LSMGO MT": fmt(x["lsmgo_mt"]),
                    "Bunker USD": fmt(x["bunker_usd"]), "Port DA USD": fmt(x["port_da_usd"]),
                    "Lain USD": fmt(x["other_usd"]), "Total USD": fmt(x["total_usd"])} for x in nominal["ledger"]]),
                    hide_index=True, width="stretch")
            scenario_names = {"minimum": "Minimum", "nominal": "Nominal", "maximum": "Maksimum"}
            st.dataframe(pd.DataFrame([{"Skenario": scenario_names[label], "Muatan MT": fmt(row["cargo_mt"]),
                "Batas MT": fmt(row.get("capacity", {}).get("limit_mt")), "Hari": fmt(row.get("days")),
                "Freight USD/MT": fmt(row.get("freight_usd_mt")),
                "Status": "Lolos pemeriksaan awal" if row["feasible"] else row.get("error", "Kapasitas tidak cukup")}
                for label, row in scenarios.items()]), hide_index=True, width="stretch")
    st.caption("Rute: " + result["case"]["ports"]["load"]["name"] + " → " + result["case"]["ports"]["discharge"]["name"]
               + " · Jarak: " + fmt(result["case"]["distance_nm"]) + " NM · Dihitung: " + price_time(result["calculated_at"]))
    with st.expander("Commercial brief", expanded=True):
        brief = commercial_brief(result)
        st.markdown(brief)
        st.download_button("Download brief", brief, "commercial_brief.md", mime="text/markdown")
        st.download_button("Download Detailed Brief", json.dumps(serializable(result), ensure_ascii=False, indent=2),
                        "freight_result.json", mime="application/json")


def matrix_view(result, root):
    case = result["case"]
    with st.expander("Spread matrix"):
        choices = port_catalog(str(root / "data/raw/Ports.xlsx"), (root / "data/raw/Ports.xlsx").stat().st_mtime_ns)
        a, b = st.columns(2)
        origins = a.multiselect("Port muat", choices, default=[(case["ports"]["load"]["name"], case["ports"]["load"]["country"])],
                               format_func=lambda p: p[0] + ", " + p[1])
        destinations = b.multiselect("Port bongkar", choices, default=[(case["ports"]["discharge"]["name"], case["ports"]["discharge"]["country"])],
                                    format_func=lambda p: p[0] + ", " + p[1])
        a, b, c = st.columns(3)
        family = a.selectbox("Kelas matrix", list(case["profiles"]))
        basis = b.selectbox("Muatan matrix", ["nominal", "minimum", "maximum"],
                            format_func={"nominal": "Nominal", "minimum": "Minimum", "maximum": "Maksimum"}.get)
        display = c.selectbox("Tampilan", ["Flat", "Delta"])
        rows_input = []
        for side, selected in (("load", origins), ("discharge", destinations)):
            reference = case["ports"][side]
            for chosen_port in selected:
                if tuple(chosen_port) != (reference["name"], reference["country"]):
                    rows_input.append({"Sisi": side, "Port": chosen_port[0], "Negara": chosen_port[1],
                        "Rate MT/hari": float(reference["rate_mt_day"]), "Port DA USD": float(reference["port_da_usd"]),
                        "Batas draft m": None, "Terms": reference["terms"],
                        "Margin waktu %": float(reference["time_margin_percent"])})
        overrides = {}
        edited_ports = rows_input
        if rows_input:
            st.caption("Parameter port tambahan; nilai awal diwariskan dari input muat/bongkar.")
            edited_ports = st.data_editor(pd.DataFrame(rows_input), key="matrix_ports_" + result["input_sha256"],
                hide_index=True, disabled=["Sisi", "Port", "Negara"],
                column_config={"Terms": st.column_config.SelectboxColumn(options=list(TERMS)),
                    "Rate MT/hari": st.column_config.NumberColumn(min_value=0.0, format="%.2f"),
                    "Port DA USD": st.column_config.NumberColumn(min_value=0.0, format="%.2f"),
                    "Batas draft m": st.column_config.NumberColumn(min_value=0.0, format="%.2f"),
                    "Margin waktu %": st.column_config.NumberColumn(min_value=0.0, format="%.2f")}).to_dict("records")
            for row in edited_ports:
                for field in ("Rate MT/hari", "Port DA USD", "Batas draft m", "Margin waktu %"):
                    row[field] = None if pd.isna(row[field]) else row[field]
                overrides[(row["Sisi"], row["Port"], row["Negara"])] = {
                    "rate_mt_day": str(row["Rate MT/hari"]), "port_da_usd": str(row["Port DA USD"]),
                    "draft_limit_m": None if row["Batas draft m"] is None else str(row["Batas draft m"]),
                    "terms": row["Terms"], "time_margin_percent": str(row["Margin waktu %"])}
        key = digest({"case": result["input_sha256"], "origins": origins, "destinations": destinations,
                      "family": family, "basis": basis, "ports": edited_ports})
        saved = st.session_state.get("matrix")
        if origins and destinations and (not saved or saved[0] != key):
            try:
                with st.spinner("Menghitung matrix…"):
                    st.session_state["matrix"] = (key, matrix(case, origins, destinations, family, root, basis, overrides))
            except ValueError as error:
                st.session_state.pop("matrix", None)
                st.error(str(error))
        elif not origins or not destinations:
            st.session_state.pop("matrix", None)
            st.caption("Pilih minimal satu port muat dan satu port bongkar.")
        saved = st.session_state.get("matrix")
        if origins and destinations and saved and saved[0] == key:
            cells = saved[1]
            rows = []
            for dest in destinations:
                row = {"PoD": dest[0] + ", " + dest[1]}
                for origin in origins:
                    cell = next(x for x in cells if tuple(x["origin"]) == tuple(origin) and tuple(x["destination"]) == tuple(dest))
                    row[origin[0] + ", " + origin[1]] = fmt(cell["rate"] if display == "Flat" else cell["delta"])
                rows.append(row)
            event = st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch",
                key="matrix_grid_" + key + display, on_select="rerun", selection_mode="single-cell")
            selected_cells = event.selection.cells
            if selected_cells and selected_cells[0][1] != "PoD":
                index, column = selected_cells[0]
                dest = destinations[index]
                origin = next(p for p in origins if p[0] + ", " + p[1] == column)
                chosen = next(i for i, cell in enumerate(cells)
                    if tuple(cell["origin"]) == tuple(origin) and tuple(cell["destination"]) == tuple(dest))
            else:
                chosen = st.selectbox("Rincian sel", range(len(cells)),
                    format_func=lambda i: cells[i]["origin"][0] + " → " + cells[i]["destination"][0])
            cell = cells[chosen]
            if cell.get("result"):
                st.caption("Port baru mewarisi rate, Port DA, terms, kalender dan margin waktu input; batas draft baru belum diisi." if cell["inherited_ports"] else "Kasus dasar.")
                st.markdown(commercial_brief(cell["result"]))
            else:
                st.warning(cell.get("error", "Opsi tidak tersedia."))
            st.download_button("Download matrix", json.dumps(serializable(cells), ensure_ascii=False, indent=2),
                               "spread_matrix.json", mime="application/json")
        st.caption("Flat: USD/MT. Delta: selisih terhadap rute dasar. Maksimum 25 sel; bukan selisih laba.")


def render(root: Path, output_root=None):
    st.set_page_config(page_title="PILOG Freight Desk", page_icon="⚓", layout="wide")
    st.html(STYLE)
    runtime = (output_root or root / "outputs") / "market_cache"
    try:
        market = fresh_market()
        try:
            save_runtime_snapshot(market, runtime)
        except OSError:
            pass
        market_error = None
    except Exception as error:
        market = latest_saved(root, runtime)
        market_error = str(error)
    if market is None:
        st.error("Snapshot pasar belum tersedia.")
        return
    with st.sidebar:
        st.image(str(root / "public/Pupuk_Indonesia_Logistik.png"), width=100)
        if st.button("Kasus baru", width="stretch"):
            for key in ("freight_case", "freight_result", "matrix"):
                st.session_state.pop(key, None)
            st.rerun()
        upload = st.file_uploader("Buka paket kasus", type=["json"])
        if st.button("Buka kasus", disabled=upload is None, width="stretch"):
            try:
                st.session_state["freight_case"] = import_case(upload.getvalue())
                st.session_state["widget_generation"] = st.session_state.get("widget_generation", 0) + 1
                st.session_state["replay_case"] = True
                st.session_state.pop("freight_result", None)
                st.session_state.pop("matrix", None)
                st.rerun()
            except (ValueError, KeyError, TypeError) as error:
                st.error(str(error))
        st.caption("Internal PI/PILOG")
    if "freight_case" not in st.session_state:
        st.session_state["freight_case"] = default_case(root, market)
        st.session_state["replay_case"] = False
    case = st.session_state["freight_case"]
    # New feed affects default market inputs, never manual overrides or imported replay.
    if not st.session_state.get("replay_case"):
        case["market_snapshot"] = deepcopy(market)
        case["report_snapshot"] = read_assessments(root)
        for grade, key in (("VLSFO", "fo_price_usd_mt"), ("LSMGO", "do_price_usd_mt")):
            field = "fuel." + grade + ".value"
            if case["sources"].get(field, {}).get("status") != "manual_override":
                case["fuel"][grade] = dict(deepcopy(market["bunkers"][key]), requested_grade=grade,
                                           proxy=True, original_value=market["bunkers"][key]["value"])
    st.title("Automated Freight Desk PILOG    ")
    if market_error:
        st.caption("Fearnpulse tidak terhubung; menggunakan data pasar yang tersimpan.")
    inputs(case, root)
    market_context(case)
    with st.sidebar:
        st.download_button("Download kasus", export_case(case), "pilog_freight_case.json",
                           mime="application/json", width="stretch")
    if st.button("Hitung freight", type="primary", width="stretch"):
        try:
            if st.session_state["input_errors"]:
                raise ValueError("; ".join(st.session_state["input_errors"]))
            st.session_state["freight_result"] = evaluate(case)
        except (ValueError, KeyError, TypeError) as error:
            st.session_state.pop("freight_result", None)
            st.error("Periksa input: " + str(error))
    result = st.session_state.get("freight_result")
    if result and result["input_sha256"] == digest(case):
        results_view(result)
        matrix_view(result, root)
    elif result:
        st.caption("Input berubah. Hitung freight untuk memperbarui hasil.")
