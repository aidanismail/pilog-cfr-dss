"""Restrained blue/white interface around the existing I4 workflow."""
import json
import re
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

from pilog_cfr_dss.application.interactive_case import InteractiveCase
from pilog_cfr_dss.reporting.iteration_04 import commercial_brief
from pilog_cfr_dss.application.market_case import new_market_case, apply_profile, apply_market, apply_case_basis, catalog, voyage_catalog, apply_voyage, compare_profiles, demo_case
from pilog_cfr_dss.sources.fearnpulse import latest_saved, fetch_snapshot, save_snapshot
from pilog_cfr_dss.models.tender_clock import round_schedule
from pilog_cfr_dss.reporting.formatting import price_time as time_label
from pilog_cfr_dss.reporting.formatting import number_text
from pilog_cfr_dss.validation.case_basis import BASIS_VERSION, COMMISSION_KEYS
from pilog_cfr_dss.validation.cost_forecast import COST_KEYS
from pilog_cfr_dss.ui.presentation import active_inputs, source_label
from pilog_cfr_dss.application.tender_examples import generate_example, record_applied_example
from pilog_cfr_dss.reporting.iteration_04 import cost_change_lines, pricing_bridge_lines, price_reference


LABELS = {
    "cargo_mt": "Volume cargo (MT)", "distance_nm": "Jarak satu arah (NM)",
    "loading_rate_mt_day": "Kecepatan muat (MT/hari)", "discharge_rate_mt_day": "Kecepatan bongkar (MT/hari)",
    "waiting_days": "Waktu tunggu baseline (hari)", "dwt_mt": "DWT kapal (MT)",
    "speed_knots": "Kecepatan saat bermuatan (knot)", "sea_fo_mt_day": "Konsumsi fuel oil saat berlayar (MT/hari)",
    "sea_do_mt_day": "Konsumsi diesel oil saat berlayar (MT/hari)", "port_do_mt_day": "Konsumsi diesel oil di pelabuhan (MT/hari)",
    "running_usd_day": "Biaya operasional kapal harian (USD/hari)", "fo_price_usd_mt": "Harga fuel oil (USD/MT)",
    "do_price_usd_mt": "Harga diesel oil (USD/MT)", "port_other_total_usd": "Total pelabuhan dan biaya lain (USD)",
    "freight_commission_fraction": "Komisi freight (fraksi)", "broker_fraction": "Komisi broker (fraksi)",
    "additional_commission_fraction": "Komisi tambahan (fraksi)",
}
STYLE = """
<style>
h1,h2,h3 {font-weight:650; letter-spacing:-.025em;}
.workspace-header {border-top:4px solid #1E70B8;padding:16px 0;margin-bottom:8px;}
.workspace-header .eyebrow {color:#52697B;font-size:11px;font-weight:700;letter-spacing:.14em;}
.workspace-header h1 {color:#142D43;font-size:36px;line-height:1.12;margin:0;}
.workspace-header p {color:#52697B;font-size:15px;margin:0;}
.workflow-strip {display:flex;flex-wrap:wrap;gap:12px 28px;border-top:1px solid #DFE7EE;
 border-bottom:1px solid #DFE7EE;padding:13px 0;margin:0 0 20px;color:#52697B;font-size:12px;}
.workflow-strip strong {color:#1E70B8; margin-right:6px;}
.workflow-strip a {color:#52697B;text-decoration:none;}
.workflow-strip a:hover {color:#1E70B8;text-decoration:underline;}
.section-heading {margin:20px 0 14px;border-top:1px solid #DFE7EE;padding-top:18px;}
section[data-testid="stSidebar"] [data-testid="stImage"] {margin:0 auto 8px;}
.section-heading .number {font-size:11px;font-weight:700;letter-spacing:.13em;color:#1E70B8;}
.section-heading h2 {font-size:27px;color:#142D43;margin:3px 0 4px;}
.section-heading p {font-size:14px;color:#52697B;margin:0;}
.decision-banner {border-left:5px solid #1E70B8;background:#F4F7FA;padding:20px 24px;margin-bottom:18px;}
.decision-banner.no-go {border-left-color:#B44136;}
.decision-banner .action {font-size:32px;font-weight:750;color:#142D43;letter-spacing:-.03em;}
.decision-banner p {margin:5px 0 0;color:#344F64;line-height:1.5;}
.source-note {font-size:12px;color:#52697B;line-height:1.5;}
@media(max-width:640px) {.workspace-header h1 {font-size:31px;} .workflow-strip {gap:10px 16px;}}
</style>
"""


def fmt(value, *, minimum=False):
    """Display formatting only, never inputs to the financial engine."""
    return number_text(value, minimum=minimum)


def display_reference(value):
    """Neutral display copy; preserve original provenance in input snapshots."""
    if isinstance(value, dict):
        return {key: display_reference(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [display_reference(item) for item in value]
    if not isinstance(value, str):
        return value
    value = value.replace("Mentor/user I4 plan and D-040/D-042", "Parameter kasus I4")
    value = value.replace("mentor aggregate interpretation from Sby audit", "interpretasi total biaya pada audit sheet Sby")
    return re.sub(r"\bmentor\b", "peninjau domain", value, flags=re.IGNORECASE)


def section(number, title):
    st.html(f'<div class="section-heading" id="pilog-step-{escape(number)}"><span class="number">{escape(number)}</span>'
            f'<h2>{escape(title)}</h2></div>')


def _close_editor(key):
    st.session_state["_close_editor"] = key
    st.rerun()


def sidebar(root, case, output_root):
    with st.sidebar:
        st.image(str(root / "public/Pupuk_Indonesia_Logistik.png"), width=62)
        st.divider()
        st.markdown("**Kasus kerja**")
        for label, kind in (("Muat contoh GO", "go"), ("Muat contoh NO GO", "no-go-floor"), ("Muat NO GO ekonomi", "no-go-economics")):
            if st.button(label, width="stretch"):
                snapshot = case.context.get("market_snapshot") or st.session_state.get("available_market")
                example = demo_case(root, snapshot, output_root / "ui_cases", kind,
                    case.context.get("vessel_profile", {}).get("profile_id"),
                    voyage_id=case.context.get("voyage_estimate", {}).get("voyage_id"))
                st.session_state["case"] = example
                st.rerun()
        if st.button("Kasus baru", width="stretch", help="Salin basis I4; hitung freight baru. Bid lama tidak dibawa."):
            revised = case.revise()
            apply_case_basis(revised, root)
            st.session_state["case"] = revised
            st.rerun()
        with st.expander("Tentang contoh"):
            st.caption("Bid contoh sintetis; sumber dan asumsi tercatat di audit.")
        st.divider()
        st.markdown("**Draft lokal**")
        if st.button("Simpan draft", width="stretch"):
            try:
                path = case.save(output_root / "ui_cases")
                st.success("Draft tersimpan.")
                st.caption(str(path.relative_to(output_root)))
            except (ValueError, OSError, KeyError) as error:
                st.error(f"Draft belum tersimpan: {error}")
        drafts = output_root / "ui_cases"
        paths = sorted(drafts.glob("ui_*/revision_*/case_fixture.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:50]
        selected = st.selectbox("Buka draft tersimpan", [None, *paths], format_func=lambda p:
                                "Pilih draft" if p is None else f"{p.parent.parent.name[-8:]} · {p.parent.name}")
        if st.button("Buka draft", disabled=selected is None, width="stretch"):
            try:
                st.session_state["case"] = InteractiveCase.reopen(selected, drafts)
                st.rerun()
            except (ValueError, OSError, KeyError) as error:
                st.error(f"Draft tidak dapat dibuka: {error}")
        st.divider()
        st.caption("Internal PI/PILOG")


def profile_name(profile):
    fields = profile.get("fields", profile)
    return profile["vessel_class"] + " · " + fmt(fields["dwt_mt"]) + " DWT · " + fmt(fields["speed_knots"]) + " knot"


def voyage_selector(case, root, editing):
    voyages = voyage_catalog(root)
    by_id = {v["voyage_id"]: v for v in voyages["voyages"]}
    current = case.context.get("voyage_estimate", {})
    current_id = current.get("voyage_id")
    if current_id not in by_id:
        current_id = next((vid for vid,v in by_id.items() if
                          v["fields"]["loading_port"] == case.values()["loading_port"] and
                          v["fields"]["discharging_port"] == case.values()["discharging_port"]), next(iter(by_id)))
    selected = st.selectbox("Pilih Voyage Estimate", list(by_id), index=list(by_id).index(current_id),
        format_func=lambda vid: by_id[vid]["label"] + " · " + fmt(by_id[vid]["fields"]["cargo_mt"]) + " MT",
        disabled=case.fixed or editing, key="voyage_" + case.draft_id + "_" + str(case.revision))
    if selected != current_id and not case.fixed and not editing:
        apply_voyage(case, by_id[selected], root)
        st.rerun()
    if current.get("source_sha256") != voyages["source_sha256"]:
        st.caption("Kasus memakai versi workbook sebelumnya.")
        if st.button("Gunakan workbook terbaru", disabled=editing):
            st.session_state["case"] = new_market_case(root, case.context["market_snapshot"],
                case.context["vessel_profile"]["profile_id"], selected)
            st.rerun()


def profile_selector(case, root, editing):
    profiles = catalog(root)
    by_id = {profile["profile_id"]: profile for profile in profiles["profiles"]}
    current_id = case.context["vessel_profile"]["profile_id"]
    selected = st.selectbox("Pilih profil kapal", list(by_id), index=list(by_id).index(current_id),
        format_func=lambda pid: profile_name(by_id[pid]),
        disabled=case.fixed or editing, key="profile_" + case.draft_id + "_" + str(case.revision),
        help="Paket spesifikasi dari Voyage Estimate. Pilihan ini dipakai di seluruh perhitungan Step 2.")
    if selected != current_id and not case.fixed and not editing:
        apply_profile(case, by_id[selected], profiles["policy"])
        st.rerun()


def review_data(case, root, editing=False):
    voyage_choice, vessel_choice = st.columns(2)
    with voyage_choice:
        voyage_selector(case, root, editing)
    with vessel_choice:
        profile_selector(case, root, editing)
    inputs = active_inputs(case)
    values = {key: row["value"] for key, row in inputs.items()}
    profile = case.context["vessel_profile"]
    snapshot = case.context["market_snapshot"]
    target = case.context["pricing"]["target_tce"]
    try:
        market = case.market_summary()
    except (ValueError, KeyError, TypeError, ArithmeticError):
        market = {}
    columns = st.columns([1, 1.15], gap="medium")
    with columns[0], st.container(border=True):
        st.markdown("**Pengiriman & spesifikasi kapal**")
        st.write(values["cargo_description"])
        st.markdown(f"**{values['loading_port']} → {values['discharging_port']}**")
        volume, distance = st.columns(2)
        volume.metric("Muatan (MT)", fmt(values["cargo_mt"]))
        distance.metric("Jarak satu arah (NM)", fmt(values["distance_nm"]))
        st.caption("Jarak: OD · " + case.context["distance_reference"]["sheet"] + "!" + case.context["distance_reference"]["cell"])
        st.dataframe([{"Spesifikasi": label, "Nilai": fmt(values[key]), "Satuan": unit}
            for label, key, unit in (
                ("DWT", "dwt_mt", "MT"), ("Kecepatan bermuatan", "speed_knots", "knot"),
                ("Fuel oil saat berlayar", "sea_fo_mt_day", "MT/hari"),
                ("Diesel oil saat berlayar", "sea_do_mt_day", "MT/hari"),
                ("Diesel oil di pelabuhan", "port_do_mt_day", "MT/hari"),
                ("Operasional kapal", "running_usd_day", "USD/hari"))],
            hide_index=True, width="stretch")
        # st.caption("Spesifikasi: Voyage Estimate.xlsx · " + profile["sheet"])
        # if profile.get("source_status") == "simulation_only_workbook_vessel_profile":
        #     st.caption("Spesifikasi kapal: asumsi demo.")
        # if case.context.get("voyage_estimate"):
        #     st.caption("Voyage: Voyage Estimate.xlsx · " + case.context["voyage_estimate"]["sheet"])
        # if case.context.get("cost_forecast"):
        #     st.caption("Perubahan operasi/biaya mengikuti estimasi terbaru.")
        with st.expander("Input pelabuhan"):
            st.dataframe([{"Input": label, "Nilai": fmt(values[key]), "Satuan": unit,
             } for label, key, unit in (
                    ("Kecepatan muat", "loading_rate_mt_day", "MT/hari"),
                    ("Kecepatan bongkar", "discharge_rate_mt_day", "MT/hari"),
                    ("Waktu tunggu", "waiting_days", "hari"),
                    ("Pelabuhan dan biaya lain", "port_other_total_usd", "USD"))],
                hide_index=True, width="stretch")
            #st.caption("Produktivitas, waktu tunggu dan biaya pelabuhan: asumsi demo pada sheet voyage terpilih.")
    with columns[1], st.container(border=True):
        st.markdown("**Harga acuan**")
        target_tab, bunker_tab, index_tab = st.tabs(["Target harian", "Harga bunker", "Indeks urea"])
        with target_tab:
            quote = snapshot["tc_rates"][profile["market_family"]]
            st.metric("Target hasil harian (USD/hari)", fmt(target["value"]),
                help="Sasaran hasil sebelum biaya operasional kapal. Dipakai menghitung indikasi freight.")
            st.caption(profile_name(profile) + " → acuan " + quote["series"])
            if target["source_status"] == "simulation_only_user_input":
                st.caption("Target: input manual. Benchmark Fearnpulse tetap sebagai pembanding.")
            else:
                st.caption("Fearnpulse · 1-year T/C · " + quote["source_observed_on"])
            st.caption("Dipakai untuk target harian indikasi freight, bukan biaya sewa tambahan.")
            if profile["market_class_proxy"]:
                st.caption("Handymax memakai acuan pasar Handysize 38k sebagai proxy kelas.")
            with st.expander("Seluruh acuan pasar kapal"):
                st.dataframe([{"Seri": record["series"], "USD/hari": fmt(record["value"]),
                    "Tanggal data": record["source_observed_on"],
                    "Peran": "Acuan profil ini" if family == profile["market_family"] else "Acuan kelas lain"}
                    for family, record in snapshot["tc_rates"].items()], hide_index=True, width="stretch")
        with bunker_tab:
            bunker_rows = []
            for key, label in (("fo_price_usd_mt", "Fuel oil"), ("do_price_usd_mt", "Diesel oil")):
                record = inputs[key]
                source = source_label(record)
                date = snapshot["bunkers"][key]["source_observed_on"] if source == "Fearnpulse" else (
                    time_label(case.context["cost_forecast"]["recorded_at"]) if source == "Estimasi terbaru" else "Tidak tercatat")
                bunker_rows.append({"Bahan bakar": label, "Harga dipakai (USD/MT)": fmt(record["value"]),
                    "Sumber nilai": source, "Tanggal data": date})
            st.dataframe(bunker_rows, hide_index=True, width="stretch")
            st.caption("Singapore 380 CST → fuel oil · Singapore MGO → diesel oil.")
            st.caption("Harga × kebutuhan bahan bakar masuk biaya voyage. Singapura adalah acuan harga, bukan lokasi bunkering.")
            with st.expander("Harga pasar bunker pembanding"):
                st.dataframe([{"Seri": record["series"], "USD/MT": fmt(record["value"]),
                    "Tanggal data": record["source_observed_on"]} for record in snapshot["bunkers"].values()],
                    hide_index=True, width="stretch")
        with index_tab:
            st.metric("Indeks urea FOB SEA (USD/MT)", fmt(market.get("index_usd_mt")))
            st.caption("Rata-rata midpoint Argus dan Fertecon; digunakan untuk FOB barang.")
            st.dataframe([{"Sumber": name.title(), "Low": fmt(record["low"]), "High": fmt(record["high"]),
                "Tanggal data": record.get("observation_date", "Tidak tersedia")} for name, record in case.context["market_index"].items()],
                hide_index=True, width="stretch")
        st.caption("Fearnpulse diambil " + time_label(snapshot["fetched_at"]))
    refresh, apply = st.columns(2)
    with refresh:
        if st.button("Perbarui data Fearnpulse", disabled=editing):
            try:
                with st.spinner("Mengambil tarif dan harga bunker…"):
                    latest = fetch_snapshot()
                    save_snapshot(latest, root)
                st.session_state["available_market"] = latest
                st.success("Snapshot baru tersedia; harga kasus belum diubah.")
            except (ValueError, OSError, KeyError, TypeError, ArithmeticError) as error:
                st.error("Data pasar belum diperbarui: " + str(error))
    with apply:
        available = st.session_state.get("available_market", snapshot)
        newer = available["snapshot_id"] != snapshot["snapshot_id"]
        manual_market = target["source_status"] == "simulation_only_user_input" or any(
            row["source_status"] == "simulation_only_user_input" for row in case.rows if row["key"] in {"fo_price_usd_mt", "do_price_usd_mt"})
        label = "Gunakan data pasar pada kasus baru" if case.fixed else "Gunakan data pasar terbaru"
        if st.button(label, disabled=editing or (not newer and not manual_market)):
            if case.fixed:
                case = case.revise()
                st.session_state["case"] = case
            apply_market(case, available)
            st.rerun()
    with st.expander("Sumber dan asumsi input"):
        st.dataframe(pd.DataFrame(display_reference(list(inputs.values()))).rename(columns={
            "key": "Variabel", "value": "Nilai dipakai", "unit": "Satuan", "source_status": "Status sumber",
            "source_reference": "Referensi", "note": "Catatan", "role": "Peran"}), hide_index=True, width="stretch")
        st.caption("Jarak OD belum diverifikasi dengan rute navigasi independen.")
        st.link_button("Fearnpulse · sumber pasar", "https://fearnpulse.com/#2")
        st.json(display_reference({key: case.context[key] for key in ("market_index", "pricing", "oe_hps", "distance_reference")}))


def input_editor(case):
    key = "edit_input_" + case.draft_id
    editing = st.toggle("Ubah input kasus", key=key, disabled=case.fixed)
    if case.fixed:
        st.caption("Harga tetap. Gunakan estimasi biaya terbaru untuk menilai perubahan biaya; Kasus baru untuk penawaran baru.")
    if not editing:
        return False
    st.info("Terapkan input untuk menghitung ulang. Gunakan titik desimal tanpa pemisah ribuan.")
    values = case.values()
    fields = {row["key"]: row for row in case.rows}
    with st.form("inputs_" + case.draft_id):
        voyage_tab, vessel_tab, price_tab = st.tabs(["Voyage & pelabuhan", "Profil kapal & biaya", "Harga & komisi"])
        edits = {}
        groups = [
            (voyage_tab, ["cargo_mt", "distance_nm", "loading_rate_mt_day", "discharge_rate_mt_day", "waiting_days", "port_other_total_usd"]),
            (vessel_tab, ["dwt_mt", "speed_knots", "sea_fo_mt_day", "sea_do_mt_day", "port_do_mt_day", "running_usd_day", "fo_price_usd_mt", "do_price_usd_mt"]),
            (price_tab, ["freight_commission_fraction", "broker_fraction", "additional_commission_fraction"]),
        ]
        for tab, keys in groups:
            with tab:
                columns = st.columns(2)
                for i, field in enumerate(keys):
                    with columns[i % 2]:
                        edits[field] = st.text_input(LABELS[field], values[field], key=f"input_{case.draft_id}_{field}",
                                                   disabled=field in (*COMMISSION_KEYS, "distance_nm"),
                                                   help=display_reference(fields[field]["source_reference"]))
        with price_tab:
            st.caption("Seluruh komisi 0%. OE/HPS adalah batas harga barang PI.")
            target = st.text_input("Target hasil harian sebelum biaya operasional kapal (USD/hari)", case.context["pricing"]["target_tce"]["value"])
            floor = st.text_input("OE/HPS barang PI (USD/MT)", case.context["oe_hps"]["value"])
            observations = {}
            for publisher in ("argus", "fertecon"):
                lo, hi = st.columns(2)
                source = case.context["market_index"][publisher]
                observations[publisher] = {
                    "low": lo.text_input(publisher.title() + " low (USD/MT)", source["low"]),
                    "high": hi.text_input(publisher.title() + " high (USD/MT)", source["high"]),
                }
        submitted = st.form_submit_button("Terapkan input", type="primary")
    if submitted:
        try:
            case.apply_inputs(edits, target_tce=target, observations=observations, oe_hps=floor)
            _close_editor(key)
        except (ValueError, KeyError, TypeError) as error:
            st.error(f"Input belum diterapkan: {error}")
    return True


def voyage_view(case, root, output_root, editing):
    section("02", "Voyage Economics")
    profile = case.context["vessel_profile"]
    values = case.current_values()
    profiles = catalog(root)
    st.caption("Menggunakan " + profile_name(profile) + " · " +
               values["loading_port"] + " → " + values["discharging_port"])
    with st.expander("Pilihan kapal dan dasar perbandingan"):
        st.dataframe([{"Profil": profile_name(p), "Kelas": p["vessel_class"], "DWT": fmt(p["fields"]["dwt_mt"]),
                       "Kecepatan (knot)": fmt(p["fields"]["speed_knots"]), "Fuel oil berlayar (MT/hari)": fmt(p["fields"]["sea_fo_mt_day"]),
                       "Acuan pasar": p["market_family"] + (" (proxy kelas)" if p["market_class_proxy"] else "")}
                      for p in profiles["profiles"]], hide_index=True, width="stretch")
        st.caption("Spesifikasi: workbook. Acuan pendapatan harian: Fearnpulse. Pilihan kapal tetap manual.")
        common_rate = st.text_input("Freight pembanding (USD/MT)", case.context["freight_tender"]["value"] if case.fixed else "",
            key="compare_rate_" + case.draft_id, placeholder="Kosong: indikasi profil terpilih")
        if st.button("Bandingkan profil", disabled=editing):
            try:
                with st.spinner("Menghitung setiap profil…"):
                    comparison = compare_profiles(case, root, output_root / "ui_cases", common_rate.strip() or None)
                st.session_state["profile_comparison"] = {"basis": case.fingerprint, "rows": comparison, "input_rate": common_rate}
            except (ValueError, KeyError, TypeError, OSError, ArithmeticError) as error:
                st.error("Perbandingan belum dapat dihitung: " + str(error))
        comparison = st.session_state.get("profile_comparison", {})
        if comparison.get("basis") == case.fingerprint and comparison.get("input_rate") == common_rate:
            same, required = st.tabs(["Freight yang sama", "Tarif untuk target tiap profil"])
            with same:
                st.caption("Freight pembanding sama untuk seluruh profil. Pilihan kapal tetap manual.")
                st.dataframe([{"Profil": profile_name(row), "Freight (USD/MT)": fmt(row["common_freight_usd_mt"]),
                    "Hari": fmt(row["common_rate_economics"]["total_days"]),
                    "Biaya voyage (USD)": fmt(row["common_rate_economics"]["total_cash_cost_usd"]),
                    "Kontribusi (USD)": fmt(row["common_rate_economics"]["contribution_usd"]),
                    "Kontribusi/hari (USD)": fmt(row["common_contribution_per_day_usd"]),
                    "Kapasitas awal": "Lolos" if row["capacity_screen_passed"] else "Tidak lolos"}
                    for row in comparison["rows"]], hide_index=True, width="stretch")
            with required:
                st.dataframe([{"Profil": profile_name(row), "Target harian (USD/hari)": fmt(row["target_tce_usd_day"]),
                    "Hari": fmt(row["baseline"]["total_days"]), "Freight indikatif (USD/MT)": fmt(row["computed_freight_usd_mt"]),
                    "Kontribusi (USD)": fmt(row["baseline"]["contribution_usd"]), "Dihitung": time_label(row["calculated_at"])}
                    for row in comparison["rows"]], hide_index=True, width="stretch")
                st.caption("Target kelas berbeda dapat menghasilkan tarif berbeda; ini belum membuktikan penerimaan pasar.")
    left, right = st.columns([1, 2])
    error_key = "voyage_error_" + case.draft_id
    if st.session_state.get(error_key):
        st.error("Voyage belum dapat dihitung: " + st.session_state[error_key])
    with left:
        if st.button("Hitung ekonomi voyage", type="primary", disabled=editing, width="stretch"):
            try:
                with st.spinner("Menghitung durasi, biaya dan tarif…"):
                    case.prepare(output_root / "ui_cases")
                st.session_state.pop(error_key, None)
                st.rerun()
            except (ValueError, TypeError, KeyError, OSError, ArithmeticError) as error:
                st.session_state[error_key] = str(error)
                st.rerun()
    with right:
        if case.fixed:
            st.caption("Freight tetap tidak berubah saat dihitung ulang.")
    report = case.preparation
    if editing:
        return
    if report is None:
        if case.fixed:
            st.caption("Freight tetap " + fmt(case.context["freight_tender"]["value"]) + " USD/MT · ditetapkan " + time_label(case.context["freight_tender"].get("fixed_at")))
        else:
            st.caption("Belum dihitung.")
        return
    base, pricing = report["baseline"], report["pricing"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Durasi voyage (hari)", fmt(base["total_days"]))
    c2.metric("Biaya voyage (USD)", fmt(base["total_cash_cost_usd"]))
    c3.metric("Indikasi freight (USD/MT)", fmt(pricing["computed_freight_usd_mt"]))
    c4.metric("Freight tetap (USD/MT)" if case.fixed else "Kontribusi PILOG (USD)", fmt(pricing["freight_tender_usd_mt"]) if case.fixed else fmt(base["contribution_usd"]))
    st.caption("Dihitung " + time_label(pricing.get("calculated_at")) +
               (" · Freight ditetapkan " + time_label(case.context["freight_tender"].get("fixed_at")) if case.fixed else ""))
    duration, costs = st.columns(2)
    with duration, st.container(border=True):
        st.markdown("**Durasi & kebutuhan bahan bakar**")
        st.dataframe([{"Komponen": title, "Nilai": fmt(base[key]), "Satuan": unit} for title, key, unit in (
            ("Hari laut", "sea_days", "hari"), ("Hari muat", "loading_days", "hari"),
            ("Hari bongkar", "discharge_days", "hari"), ("Waktu tunggu", "waiting_days", "hari"),
            ("Fuel oil saat berlayar", "fo_mt", "MT"), ("Diesel oil saat berlayar", "sea_do_mt", "MT"),
            ("Diesel oil di pelabuhan", "port_do_mt", "MT"))], hide_index=True, width="stretch")
    with costs, st.container(border=True):
        st.markdown("**Biaya & kontribusi PILOG**")
        st.dataframe([{"Komponen": title, "USD": fmt(base[key])} for title, key in (
            ("Fuel oil", "fo_cost_usd"), ("Diesel oil", "do_cost_usd"),
            ("Total bahan bakar", "bunker_usd"), ("Pelabuhan dan biaya lain", "port_other_usd"),
            ("Operasional kapal", "running_usd"), ("Komisi", "commission_usd"),
            ("Pendapatan freight", "revenue_usd"), ("Kontribusi PILOG", "contribution_usd"))],
            hide_index=True, width="stretch")
    with st.expander("Dasar perhitungan"):
        st.markdown(
            "- Hari laut: jarak OD ÷ kecepatan profil kapal ÷ 24.\n"
            "- Kebutuhan bahan bakar: konsumsi profil kapal × durasi yang sesuai.\n"
            "- Biaya fuel oil/diesel oil: kebutuhan masing-masing × harga bunker yang dipakai di Step 1.\n"
            "- Indikasi freight: biaya pelayaran + target harian × total hari, dibagi muatan; komisi 0%.\n"
            "- Kontribusi PILOG: pendapatan freight dikurangi biaya voyage dan komisi.")
    if not case.fixed:
        with st.expander("Harga penawaran"):
            offer = st.text_input("Freight penawaran (USD/MT)", pricing["computed_freight_usd_mt"], key="offer_" + case.draft_id + "_" + str(case.revision))
            reason = st.text_input("Alasan jika berbeda dari indikasi", key="offer_reason_" + case.draft_id + "_" + str(case.revision))
            st.caption("Indikasi berasal dari target hasil harian. Harga penawaran dipilih secara eksplisit; penerimaan buyer belum tercatat.")
        if st.button("Tetapkan freight untuk tender", type="primary"):
            try:
                case.fix_freight(output_root / "ui_cases", offer, reason)
                st.rerun()
            except (ValueError, OSError) as error:
                st.error(f"Freight belum ditetapkan: {error}")
    elif case.fixed:
        st.caption("Buyer menawar alpha; freight tetap.")


def cost_forecast_view(case, output_root, input_editing):
    if not case.fixed:
        return False
    key = "edit_cost_" + case.draft_id
    editing = st.toggle("Perbarui estimasi biaya", key=key, disabled=input_editing)
    forecast = case.context.get("cost_forecast")
    if forecast and not editing:
        st.caption("Estimasi biaya terbaru: " + time_label(forecast["recorded_at"]))
        with st.expander("Perubahan estimasi biaya"):
            st.write(forecast["reason"])
            st.dataframe([{"Parameter": LABELS[field], "Saat penawaran": case.values()[field], "Terbaru": record["value"]}
                          for field, record in forecast["overrides"].items()], hide_index=True, width="stretch")
    if not editing:
        return False
    values = case.current_values()
    with st.form("cost_forecast_" + case.draft_id):
        st.caption("Harga freight dan bid tetap. Simpan sebagai salinan estimasi baru.")
        edits = {}
        basic = ("port_other_total_usd", "fo_price_usd_mt", "do_price_usd_mt", "waiting_days")
        cols = st.columns(2)
        for index, field in enumerate(basic):
            edits[field] = cols[index % 2].text_input(LABELS[field] + " — estimasi terbaru", values[field])
        with st.expander("Parameter operasi"):
            cols = st.columns(2)
            for index, field in enumerate(field for field in COST_KEYS if field not in basic):
                edits[field] = cols[index % 2].text_input(LABELS[field] + " — estimasi terbaru", values[field])
        reason = st.text_area("Alasan perubahan biaya")
        submitted = st.form_submit_button("Terapkan estimasi biaya", type="primary")
    if submitted:
        try:
            changed = case.reforecast_costs(edits, reason)
            changed.prepare(output_root / "ui_cases")
            st.session_state["case"] = changed
            _close_editor(key)
        except (ValueError, TypeError, KeyError, OSError, ArithmeticError) as error:
            st.error("Estimasi biaya belum diterapkan: " + str(error))
    return True


def _round_heading(case, round_number):
    st.markdown("#### Putaran " + str(round_number))
    if case.context.get("auction_clock"):
        window = round_schedule(case.context["auction_clock"], round_number)[-1]
        st.caption(time_label(window["opens_at"]) + " – " + time_label(window["closes_at"]))


def tender_tables(case):
    """Read-only prices and validity from the shared deterministic engine."""
    try:
        preview = case.tender_preview()
        for round_number in sorted({row["round"] for row in preview}):
            with st.container(border=True, key="tender_round_" + str(round_number)):
                _round_heading(case, round_number)
                st.dataframe([{"Buyer": row["buyer_id"], "Alpha (USD/MT)": fmt(row["alpha_usd_mt"]),
                    "Freight (USD/MT)": fmt(row["freight_usd_mt"]), "FOB (USD/MT)": fmt(row["fob_usd_mt"]),
                    "CFR (USD/MT)": fmt(row["cfr_usd_mt"]), "Status": row["reason"]}
                    for row in preview if row["round"] == round_number], hide_index=True, width="stretch")
        with st.expander("Rincian bid"):
            st.dataframe([{"Bid ID": row["bid_id"], "Buyer": row["buyer_id"], "Putaran": row["round"],
                "Urutan": row["sequence"], "Status input": row["status"],
                "Waktu masuk": time_label(row.get("submitted_at")),
                "Berlaku sampai": time_label(row.get("valid_until"))}
                for row in preview], hide_index=True, width="stretch")
    except (ValueError, KeyError, TypeError, ArithmeticError) as error:
        st.warning("Harga bid belum dapat ditampilkan: " + str(error))


def tender_view(case, root, output_root, input_editing):
    section("03", "Tendering")
    if not case.fixed:
        st.caption("Tetapkan freight untuk membuka tender.")
        return False
    st.markdown("**Freight tetap: " + fmt(case.context["freight_tender"]["value"]) + " USD/MT**")
    st.caption("Ditetapkan " + time_label(case.context["freight_tender"].get("fixed_at")))
    key = "edit_tender_" + case.draft_id
    editing = st.toggle("Edit bid & risiko", key=key, disabled=input_editing)
    columns = ["bid_id", "buyer_id", "sequence", "alpha_usd_mt", "status", "submitted_at", "valid_until"]
    raw = case.context.get("bids", [])
    if editing:
        round_key = "round_count_" + case.draft_id
        example_key = "tender_example_draft_" + case.draft_id
        pending = st.session_state.get(example_key)
        if pending and pending["basis_fingerprint"] != case.fingerprint:
            st.session_state.pop(example_key, None)
            pending = None
        if st.button("Acak ulang bid & risiko" if raw or pending else "Isi contoh bid tiga putaran"):
            try:
                example = generate_example(case)
                st.session_state[example_key] = {"basis_fingerprint": case.fingerprint, "example": example}
                st.session_state[round_key] = 3
                st.rerun()
            except (ValueError, KeyError, TypeError, ArithmeticError) as error:
                st.error("Contoh belum dibuat: " + str(error))
        draft_risks = case.context["scenarios"]
        editor_version = str(case.revision)
        if pending:
            raw = pending["example"]["bids"]
            draft_risks = pending["example"]["scenarios"]
            editor_version += "_" + pending["example"]["metadata"]["seed"]
            st.caption("Contoh acak belum diterapkan.")
        count = max(st.session_state.get(round_key, 3), max((bid["round"] for bid in raw), default=3))
        if st.button("Tambah putaran"):
            st.session_state[round_key] = count + 1
            st.rerun()
        st.caption("FOB dan CFR ditampilkan setelah perubahan diterapkan. Freight tetap.")
        with st.form("tender_" + case.draft_id):
            edited_rounds = []
            for round_number in range(1, count + 1):
                _round_heading(case, round_number)
                grid = st.data_editor(pd.DataFrame([{k: str(bid.get(k, "")) for k in columns}
                    for bid in raw if bid["round"] == round_number], columns=columns),
                    num_rows="dynamic", hide_index=True, width="stretch",
                    column_config={
                        "bid_id": st.column_config.TextColumn("Bid ID"), "buyer_id": st.column_config.TextColumn("Buyer"),
                        "sequence": st.column_config.TextColumn("Urutan"),
                        "alpha_usd_mt": st.column_config.TextColumn("Alpha (USD/MT)"),
                        "status": st.column_config.SelectboxColumn("Status", options=["active", "withdrawn", "expired", "replaced"]),
                        "submitted_at": st.column_config.TextColumn("Waktu masuk (ISO + zona)"),
                        "valid_until": st.column_config.TextColumn("Berlaku sampai (ISO + zona)"),
                    }, key="bid_grid_" + case.draft_id + "_" + editor_version + "_" + str(round_number))
                edited_rounds.append((round_number, grid))
            with st.expander("Waktu dan pilihan PI"):
                cutoff = st.text_input("Cutoff evaluasi (ISO dengan zona waktu)",
                    pending["example"]["evaluation_cutoff"] if pending else case.context["evaluation_cutoff"],
                    key="cutoff_" + case.draft_id + "_" + editor_version)
                start = st.text_input("Mulai putaran pertama (ISO dengan zona waktu)", case.context["auction_clock"]["starts_at"]) if case.context.get("auction_clock") else None
                selection = st.text_input("Bid pilihan PI (opsional)", "" if pending else case.context.get("pi_selected_bid_id") or "",
                    key="selection_" + case.draft_id + "_" + editor_version,
                    help="Kosong: kandidat ranking. Isi jika PI telah memilih bid; tidak mengubah hasil hitungan.")
                st.caption("3 menit tetap per putaran. Tambahan putaran memerlukan penyesuaian cutoff.")
            with st.expander("Skenario risiko"):
                scenario_columns = ["scenario_id", "label", "fuel_price_increase_fraction", "extra_port_days"]
                scenarios = st.data_editor(pd.DataFrame([{k: str(row.get(k, "")) for k in scenario_columns} for row in draft_risks],
                    columns=scenario_columns), hide_index=True, num_rows="dynamic", width="stretch",
                    column_config={"fuel_price_increase_fraction": st.column_config.TextColumn("Kenaikan bahan bakar (fraksi; 0.25 = 25%)"),
                                   "extra_port_days": st.column_config.TextColumn("Tambahan hari pelabuhan")},
                    key="scenario_grid_" + case.draft_id + "_" + editor_version)
            submitted = st.form_submit_button("Terapkan bid & risiko", type="primary")
        if submitted:
            try:
                bids = []
                for round_number, grid in edited_rounds:
                    for row in grid.fillna("").to_dict("records"):
                        if any(str(value).strip() for value in row.values()):
                            bids.append({**row, "round": str(round_number)})
                case.apply_tender(bids, cutoff.strip(), selection.strip() or None, start.strip() if start else None)
                case.apply_scenarios(scenarios.fillna("").to_dict("records"))
                if pending:
                    record_applied_example(case, pending["example"])
                    st.session_state.pop(example_key, None)
                _close_editor(key)
            except (ValueError, TypeError, KeyError) as error:
                st.error(f"Perubahan belum diterapkan: {error}")
    elif raw:
        if case.context.get("tender_example"):
            st.caption("Bid dan skenario risiko: contoh acak.")
        tender_tables(case)
    else:
        st.caption("Belum ada bid.")
    if st.button("Evaluasi tender & DSS", type="primary", disabled=editing or input_editing):
        try:
            with st.status("Mengevaluasi tender…", expanded=False) as status:
                case.evaluate(output_root / "ui_cases", output_root / "runs")
                status.update(label="Evaluasi tersimpan", state="complete")
            st.rerun()
        except (ValueError, TypeError, KeyError, OSError, ArithmeticError) as error:
            st.error(f"Hasil belum dapat disimpan: {error}")
    return editing


def supporting_analysis(report, fallback_parts):
    with st.expander("Analisis pendukung"):
        exposure, risk, logistics, pricing = st.tabs(["Exposure", "Risiko", "Dampak logistik", "Konsekuensi harga"])
        if not report.get("metrics") or not report.get("baseline"):
            for tab, body in zip((exposure, risk, logistics, pricing), fallback_parts):
                with tab:
                    st.markdown(body)
            return
        base, metrics, case = report["baseline"], report["metrics"], report["case"]
        review = report.get("commercial_review", {})
        if report["recommendation"]["gate_a"] != "PASS":
            st.caption("Gate B belum dievaluasi; angka freight berikut bersifat diagnostik.")
        with exposure:
            per_mt, break_even, delay = st.columns(3)
            per_mt.metric("Kontribusi per MT (USD)", fmt(metrics["contribution_per_mt_usd"]))
            break_even.metric("Freight impas (USD/MT)", fmt(review.get("break_even_offer_usd_mt", metrics["freight_break_even_usd_mt"]), minimum=True))
            buffer = metrics["additional_port_days_to_break_even"]
            delay.metric("Tambahan hari sampai impas", fmt(buffer) if buffer is not None else "—")
            if metrics["delay_buffer_status"] == "BASELINE_ALREADY_NEGATIVE":
                st.caption("Baseline sudah rugi; tidak ada buffer tambahan delay.")
            elif metrics["delay_buffer_status"] == "NO_INCREMENTAL_DAILY_COST_MODELLED":
                st.caption("Biaya harian tambahan belum dimodelkan.")
            else:
                st.caption("Sensitivitas delay hanya menambah operasional kapal dan diesel oil pelabuhan.")
            changes = cost_change_lines(report)
            if changes:
                st.markdown(display_reference("\n".join(changes)))
        with risk:
            st.markdown("**Sensitivitas biaya**")
            st.dataframe([{"Skenario": row["label"], "Kontribusi PILOG (USD)": fmt(row["economics"]["contribution_usd"]),
                "Perubahan (USD)": fmt(row["change_from_baseline_usd"]), "Dampak": row["interpretation"]}
                for row in report.get("scenarios", [])], hide_index=True, width="stretch")
            st.caption("Cakupan lanjutan: probabilitas risiko dan mitigasi/hedging.")
        with logistics:
            st.markdown("**" + case["loading_port"] + " → " + case["discharging_port"] + " · satu arah bermuatan**")
            duration, capacity = st.columns(2)
            with duration:
                st.dataframe([{"Durasi": title, "Hari": fmt(base[key])} for title, key in (
                    ("Laut", "sea_days"), ("Muat", "loading_days"), ("Bongkar", "discharge_days"),
                    ("Waktu tunggu", "waiting_days"), ("Total", "total_days"))], hide_index=True, width="stretch")
            with capacity:
                st.dataframe([{"Parameter": "Muatan", "Nilai": fmt(case["cargo_mt"]), "Satuan": "MT"},
                    {"Parameter": "DWT kapal", "Nilai": fmt(case["dwt_mt"]), "Satuan": "MT"},
                    {"Parameter": "Jarak satu arah", "Nilai": fmt(case["distance_nm"]), "Satuan": "NM"}],
                    hide_index=True, width="stretch")
                checks = report["recommendation"].get("checks", [])
                screen = next((check["status"] for check in checks if check["name"] == "Kapasitas — screen awal"), "Belum dievaluasi")
                st.caption("Screen DWT: " + screen)
            st.caption("Cakupan lanjutan: DWCC, kesiapan kapal/terminal dan jadwal/laycan.")
        with pricing:
            reference = price_reference(report)
            if reference:
                st.caption("Bid rujukan: " + reference["buyer_id"] + " / " + reference["bid_id"])
                fob, freight, cfr = st.columns(3)
                fob.metric("FOB PI (USD/MT)", fmt(reference["fob_usd_mt"]))
                freight.metric("Freight PILOG (USD/MT)", fmt(reference["freight_usd_mt"]))
                cfr.metric("CFR (USD/MT)", fmt(reference["cfr_usd_mt"]))
            st.caption("FOB = indeks + alpha buyer · CFR = FOB + freight tetap")
            st.dataframe([{"Buyer": row["buyer_id"], "Bid": row["bid_id"], "Alpha": fmt(row["alpha_usd_mt"]),
                "FOB PI": fmt(row["fob_usd_mt"]), "Freight PILOG": fmt(row["freight_usd_mt"]),
                "CFR": fmt(row["cfr_usd_mt"]), "Gap OE/HPS": fmt(row["oe_gap_usd_mt"]), "Hasil": row["reason"]}
                for row in report["tender"].get("bids", []) if row["is_latest"]], hide_index=True, width="stretch")
            st.caption("Harga dalam USD/MT · OE/HPS dan gap hanya untuk internal.")
            if review:
                with st.expander("Asal tarif dan waktu harga"):
                    st.markdown(display_reference("\n".join(pricing_bridge_lines(report))))
            else:
                st.markdown(fallback_parts[3])


def decision_view(case, editing):
    section("04", "Commercial Decision Brief")
    if editing:
        st.caption("Editor aktif. Hasil disembunyikan agar tidak terbaca sebagai hasil input yang belum diterapkan.")
        return
    report = case.result
    if report is None:
        st.caption("Belum dievaluasi.")
        return
    rec = report["recommendation"]
    action = "GO" if rec["action"] == "GO" else "NO GO"
    st.html('<div class="decision-banner ' + ("no-go" if action == "NO GO" else "") + '">' +
            '<div class="action">' + action + '</div><p>' + escape(rec["summary"]) + '</p></div>')
    text = display_reference(commercial_brief(report))
    parts = re.split(r"^## [1-5]\. .*$", text, flags=re.MULTILINE)
    def screen_body(body):
        return "\n".join(line for line in body.splitlines() if not line.startswith(("Case: ", "Dibuat (UTC): ", "Brief I4-")))
    if len(parts) == 6:
        main = screen_body(parts[1])
        # Separate the short decision statements; preserve all table rows and figures.
        main = re.sub(r"(?m)^(\*\*(?:Cakupan keputusan|GO:|NO GO:)|Kandidat tender:|Bid barang yang|Risiko utama yang|Tarif penawaran)", r"\n\1", main)
        st.markdown(main)
        supporting_analysis(report, [screen_body(body) for body in parts[2:]])
    else:
        st.markdown(text)
    with st.expander("Seluruh bid dan hasil perhitungan"):
        rows = report.get("tender", {}).get("bids", [])
        if rows:
            st.dataframe([{key: fmt(bid[key]) if key in {
                "alpha_usd_mt", "fob_usd_mt", "freight_usd_mt", "cfr_usd_mt", "oe_gap_usd_mt"} else bid.get(key) for key in (
                "bid_id", "buyer_id", "round", "alpha_usd_mt", "fob_usd_mt", "freight_usd_mt", "cfr_usd_mt",
                "oe_gap_usd_mt", "is_latest", "eligible_rank", "reason")} for bid in rows], hide_index=True, width="stretch")
        if case.run_dir:
            st.markdown(display_reference((case.run_dir / "calculation_audit.md").read_text(encoding="utf-8")))
    st.divider()
    st.caption("Dihitung " + time_label(report.get("pricing", {}).get("calculated_at")) + " · Freight ditetapkan " +
               time_label((case.context.get("freight_tender") or {}).get("fixed_at")))
    a, b, c = st.columns(3)
    a.download_button("Unduh decision brief", text, "commercial_decision_brief.md", mime="text/markdown", width="stretch")
    b.download_button("Unduh hasil JSON", json.dumps(report, ensure_ascii=False, indent=2), "result.json", mime="application/json", width="stretch")
    c.download_button("Unduh paket + snapshot", case.bundle(), report["run_id"] + ".zip", mime="application/zip", width="stretch")


def render(root: Path, output_root: Path | None = None):
    output_root = output_root or root / "outputs"
    st.set_page_config(page_title="PILOG · CFR Decision Workspace", layout="wide")
    st.html(STYLE)
    closed = st.session_state.pop("_close_editor", None)
    if closed:
        st.session_state[closed] = False
    if "available_market" not in st.session_state:
        st.session_state["available_market"] = latest_saved(root)
    if not st.session_state["available_market"]:
        st.error("Belum ada snapshot Fearnpulse. Jalankan scripts/refresh_market_inputs.py terlebih dahulu.")
        return
    if "case" not in st.session_state:
        st.session_state["case"] = new_market_case(root, st.session_state["available_market"])
    case = st.session_state["case"]
    sidebar(root, case, output_root)
    if not case.context.get("market_snapshot") or case.context.get("case_basis_version") != BASIS_VERSION:
        st.warning("Draft lama. Buat salinan dengan komisi 0% dan jarak OD; freight serta bid lama tidak diubah.")
        if st.button("Salin dengan basis terbaru"):
            st.session_state["case"] = new_market_case(root, st.session_state["available_market"])
            st.rerun()
        return
    st.html('<header class="workspace-header"><h1>CFR Decision Workspace</h1></header>')
    st.html('<nav class="workflow-strip" aria-label="Alur analisis">'
            '<a href="#pilog-step-01" target="_self"><strong>01</strong>Data & kapal</a>'
            '<a href="#pilog-step-02" target="_self"><strong>02</strong>Voyage Economics</a>'
            '<a href="#pilog-step-03" target="_self"><strong>03</strong>Tendering</a>'
            '<a href="#pilog-step-04" target="_self"><strong>04</strong>Decision Brief</a></nav>')
    section("01", "Data Pengiriman & Kapal")
    prior_editing = any(st.session_state.get(prefix + case.draft_id, False)
        for prefix in ("edit_input_", "edit_cost_", "edit_tender_"))
    review_data(case, root, prior_editing)
    editing = input_editor(case)
    cost_was_editing = st.session_state.get("edit_cost_" + case.draft_id, False)
    bid_was_editing = st.session_state.get("edit_tender_" + case.draft_id, False)
    voyage_view(case, root, output_root, editing or cost_was_editing)
    cost_editing = cost_forecast_view(case, output_root, editing or bid_was_editing)
    tender_editing = tender_view(case, root, output_root, editing or cost_editing)
    decision_view(case, editing or cost_editing or tender_editing)
