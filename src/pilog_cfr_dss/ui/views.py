"""Restrained blue/white interface around the existing I4 workflow."""
import json
import re
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

from pilog_cfr_dss.application.interactive_case import InteractiveCase
from pilog_cfr_dss.reporting.commercial_brief import commercial_brief
from pilog_cfr_dss.application.market_case import new_market_case, apply_profile, apply_route, active_catalog, voyage_catalog, apply_voyage
from pilog_cfr_dss.sources.route_distance import ports, distance
from pilog_cfr_dss.sources.urea_reports import read_reports
from pilog_cfr_dss.sources.baltic_profiles import verify_benchmarks
from pilog_cfr_dss.sources.fearnpulse import latest_saved, fetch_snapshot, save_runtime_snapshot
from pilog_cfr_dss.models.tender_clock import round_schedule
from pilog_cfr_dss.reporting.formatting import price_time as time_label
from pilog_cfr_dss.reporting.formatting import number_text
from pilog_cfr_dss.validation.case_basis import BASIS_VERSION, COMMISSION_KEYS
from pilog_cfr_dss.validation.cost_forecast import COST_KEYS
from pilog_cfr_dss.ui.presentation import source_label
from pilog_cfr_dss.application.tender_examples import generate_example, record_applied_example
from pilog_cfr_dss.reporting.commercial_brief import cost_change_lines, pricing_bridge_lines, price_reference


LABELS = {
    "cargo_mt": "Volume cargo (MT)", "distance_nm": "Jarak satu arah (NM)",
    "loading_rate_mt_day": "Kecepatan muat (MT/hari)", "discharge_rate_mt_day": "Kecepatan bongkar (MT/hari)",
    "waiting_days": "Waktu tunggu pelabuhan (hari)", "dwt_mt": "DWT kapal (MT)",
    "speed_knots": "Kecepatan saat bermuatan (knot)", "sea_fo_mt_day": "Konsumsi fuel oil saat berlayar (MT/hari)",
    "sea_do_mt_day": "Konsumsi diesel oil saat berlayar (MT/hari)", "port_do_mt_day": "Konsumsi diesel oil di pelabuhan (MT/hari)",
    "running_usd_day": "Biaya operasional kapal harian (USD/hari)", "fo_price_usd_mt": "Harga fuel oil (USD/MT)",
    "do_price_usd_mt": "Harga diesel oil (USD/MT)", "port_other_total_usd": "Total pelabuhan dan biaya lain (USD)",
    "freight_commission_fraction": "Komisi freight (fraksi)", "broker_fraction": "Komisi broker (fraksi)",
    "additional_commission_fraction": "Komisi tambahan (fraksi)",
    "bunkers_allowance_mt": "Allowance bunker (MT)",
    "constants_allowance_mt": "Allowance constants kapal (MT)",
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


@st.cache_data(ttl=60, show_spinner=False)
def _fresh_market():
    return fetch_snapshot()


@st.cache_data(ttl=3600, show_spinner=False)
def _baltic_check():
    return verify_benchmarks()


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
    from pilog_cfr_dss.application.case_package import export_case, import_case
    with st.sidebar:
        st.image(str(root / "public/Pupuk_Indonesia_Logistik.png"), width=62)
        st.divider()
        if st.button("Kasus baru", width="stretch"):
            st.session_state.pop("case", None)
            st.rerun()
        st.markdown("**Paket kasus**")
        st.download_button("Unduh kasus", export_case(case), "pilog_case.json",
                           mime="application/json", width="stretch")
        uploaded = st.file_uploader("Buka paket kasus", type=["json"])
        if st.button("Buka kasus", disabled=uploaded is None, width="stretch"):
            try:
                st.session_state["case"] = import_case(uploaded.getvalue())
                st.rerun()
            except (ValueError, OSError, KeyError, TypeError, UnicodeError) as error:
                st.error("Paket tidak dapat dibuka: " + str(error))
        st.caption("Unduh kasus sebelum refresh untuk melanjutkan input yang sama.")
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
    profiles = active_catalog(root)
    by_id = {profile["profile_id"]: profile for profile in profiles["profiles"]}
    current_id = case.context["vessel_profile"]["profile_id"]
    selected = st.selectbox("Pilih profil kapal", list(by_id), index=list(by_id).index(current_id) if current_id in by_id else 0,
        format_func=lambda pid: profile_name(by_id[pid]),
        disabled=case.fixed or editing, key="profile_" + case.draft_id + "_" + str(case.revision),
        help="Profil acuan Baltic dengan nilai tambahan dari Voyage Estimate.")
    if selected != current_id and not case.fixed and not editing:
        apply_profile(case, by_id[selected], profiles["policy"])
        st.rerun()
    if any(row.get('source_status') == 'simulation_only_user_input' and row['key'] in {
        'dwt_mt', 'speed_knots', 'sea_fo_mt_day', 'sea_do_mt_day', 'port_do_mt_day', 'running_usd_day'
    } for row in case.rows):
        st.caption('Memilih profil lain mengganti spesifikasi kapal yang diubah manual.')
def route_selector(case, root, editing):
    choices = ports(root / 'data/raw/Ports.xlsx')
    current = case.values()
    def find(name):
        return next((p for p in choices if p[0].casefold() == name.casefold()), choices[0])
    a, b = st.columns(2)
    with a:
        origin = st.selectbox('Pelabuhan muat (PoL)', choices, index=choices.index(find(current['loading_port'])),
                              format_func=lambda p: p[0] + ', ' + p[1], disabled=case.fixed or editing)
    with b:
        dest = st.selectbox('Pelabuhan bongkar (PoD)', choices, index=choices.index(find(current['discharging_port'])),
                            format_func=lambda p: p[0] + ', ' + p[1], disabled=case.fixed or editing)
    changed = (origin[0] != current['loading_port'] or dest[0] != current['discharging_port']
               or st.session_state.get('route_failure_' + case.draft_id) == (origin, dest))
    if changed:
        route_key = (origin, dest)
        failure_key = 'route_failure_' + case.draft_id
        if st.session_state.get(failure_key) != route_key and not case.fixed and not editing:
            try:
                with st.spinner('Memperbarui jarak…'):
                    ref = distance(origin, dest, root / 'data/raw/Simulasi Tarif Internasional_Mei 2025.xlsx')
                apply_route(case, origin, dest, ref)
                st.session_state.pop(failure_key, None)
                st.rerun()
            except (ValueError, OSError):
                st.session_state[failure_key] = route_key
        if origin == dest:
            st.error('Pelabuhan muat dan bongkar harus berbeda.')
        else:
            st.warning('Jarak belum tersedia. Isi jarak manual pada input di bawah.')
        return route_key
    st.session_state.pop('route_failure_' + case.draft_id, None)
    return None


def review_data(case, root, editing=False):
    pending_route = route_selector(case, root, editing)
    profile_selector(case, root, editing)
    return pending_route


def input_editor(case, pending_route=None):
    """One editable table, applied when the user commits a cell."""
    from copy import deepcopy
    from decimal import Decimal, InvalidOperation
    from pilog_cfr_dss.validation.case import number

    if case.fixed:
        st.caption("Buat kasus baru untuk mengubah input.")
        return False
    values = case.values()
    fields = {row["key"]: row for row in case.rows}
    keys = [
        "cargo_mt", "distance_nm", "loading_rate_mt_day", "discharge_rate_mt_day",
        "waiting_days", "port_other_total_usd", "dwt_mt", "speed_knots",
        "sea_fo_mt_day", "sea_do_mt_day", "port_do_mt_day", "running_usd_day",
        "fo_price_usd_mt", "do_price_usd_mt",
        "bunkers_allowance_mt", "constants_allowance_mt",
    ]
    target_raw = case.context["pricing"]["target_tce"]["value"]
    table = []
    for key in keys:
        original = values[key]
        value = None if pending_route and key == "distance_nm" else float(number(original, key))
        date = None
        if key in {'fo_price_usd_mt', 'do_price_usd_mt'} and fields[key].get('source_status') == 'observed_public_market':
            date = case.context.get('market_snapshot', {}).get('bunkers', {}).get(key, {}).get('source_observed_on')
        table.append({"Parameter": LABELS[key], "Nilai": value, "Satuan": fields[key]["unit"],
                      "Sumber": source_label(fields[key]), "Tanggal sumber": date or '—'})
    table.append({"Parameter": "TC Rates (USD/hari)", "Nilai": float(number(target_raw, "target")),
                  "Satuan": "USD/hari",
                  "Sumber": "Input manual" if case.context["pricing"]["target_tce"]["source_status"] == "simulation_only_user_input" else "Fearnpulse",
                  "Tanggal sumber": case.context['pricing']['target_tce'].get('source_observed_on', '—')})
    st.caption("Urea granular bulk · Komisi 0%")
    default_route = case.context.get('voyage_estimate', {}).get('fields', {})
    if (values['loading_port'], values['discharging_port']) != (default_route.get('loading_port'), default_route.get('discharging_port')):
        st.caption('Handling, waktu tunggu dan biaya pelabuhan tetap memakai input kasus; pemilihan rute hanya memperbarui jarak.')
    snapshot = case.context.get("market_snapshot", {})
    family = case.context.get("vessel_profile", {}).get("market_family")
    quote = snapshot.get("tc_rates", {}).get(family, {})
    st.caption("Fearnpulse diambil: " + time_label(snapshot.get("fetched_at")) +
               " · Tanggal TC Rates: " + str(quote.get("source_observed_on") or "Tidak tersedia"))
    grid = st.data_editor(pd.DataFrame(table), hide_index=True, width="stretch",
                          disabled=["Parameter", "Satuan", "Sumber", "Tanggal sumber"],
                          column_config={"Nilai": st.column_config.NumberColumn("Nilai", min_value=0.0)},
                          key=f"inputs_table_{case.draft_id}_{case.revision}_{str(pending_route)}")
    edits = {}
    try:
        for index, key in enumerate(keys):
            raw = grid.iloc[index]["Nilai"]
            if pd.isna(raw):
                if key == "distance_nm" and pending_route:
                    st.warning("Masukkan jarak satu arah (NM) untuk rute ini.")
                    return True
                raise ValueError(LABELS[key] + " wajib diisi.")
            value = Decimal(str(raw))
            if not value.is_finite() or value < 0:
                raise ValueError(LABELS[key] + " harus berupa angka tidak negatif.")
            if key in {"cargo_mt", "distance_nm", "loading_rate_mt_day", "discharge_rate_mt_day", "dwt_mt", "speed_knots"} and value <= 0:
                raise ValueError(LABELS[key] + " harus lebih besar dari nol.")
            original = values[key]
            edits[key] = original if original and Decimal(str(float(number(original, key)))) == value and not (pending_route and key == "distance_nm") else format(value.normalize(), "f")
        target_value = grid.iloc[len(keys)]["Nilai"]
        if pd.isna(target_value) or Decimal(str(target_value)) < 0:
            raise ValueError("TC Rates harus berupa angka tidak negatif.")
        target = target_raw if Decimal(str(float(number(target_raw, "target")))) == Decimal(str(target_value)) else str(target_value)
        if pending_route:
            origin, dest = pending_route
            if origin == dest:
                raise ValueError("Pelabuhan muat dan bongkar harus berbeda.")
            case = deepcopy(case)
            ref = {"value": edits["distance_nm"], "unit": "NM", "loading_port": origin[0],
                   "discharging_port": dest[0], "source_status": "simulation_only_user_input",
                   "source_reference": "Input jarak manual"}
            apply_route(case, origin, dest, ref)
        before = case.fingerprint
        observations = {p: {k: case.context["market_index"][p][k] for k in ("low", "high")}
                        for p in ("argus", "fertecon")}
        case.apply_inputs(edits, target_tce=target, observations=observations,
                          oe_hps=case.context["oe_hps"]["value"])
        if case.fingerprint != before or pending_route:
            st.session_state["case"] = case
            if pending_route:
                st.session_state.pop("route_failure_" + case.draft_id, None)
            st.rerun()
    except (ValueError, KeyError, TypeError, InvalidOperation) as error:
        st.error("Periksa input: " + str(error))
        return True
    return False


def market_comparables_view(case, root, report):
    from pilog_cfr_dss.sources.market_comparables import (
        read_comparables, read_argus_comparables, destination_country, voyage_matches, comparison_delta,
    )
    st.markdown("#### Pembanding pasar")
    values = case.current_values()
    country = destination_country(root, values["discharging_port"])
    data, argus = None, None
    try:
        data = read_comparables(root)
    except (OSError, ValueError, KeyError, TypeError, IndexError):
        pass
    try:
        argus = read_argus_comparables(root)
    except (OSError, ValueError, KeyError, TypeError, IndexError):
        pass
    a, b = st.columns(2)
    with a:
        st.markdown("**Harga urea CFR tujuan**")
        entries = []
        for publisher, source in (("Fertecon", data), ("Argus", argus)):
            record = (source.get("cfr_ports", {}).get(values["discharging_port"]) or source["cfr"].get(country)) if source else None
            if record:
                entries.append({"Sumber": publisher, "Pasar": record["label"],
                    "USD/MT": fmt(record["low"]) + "–" + fmt(record["high"]),
                    "Tanggal": record["date"], "Halaman": record["page"]})
        if entries:
            st.dataframe(entries, hide_index=True, width="stretch")
            st.caption('Nama pasar yang tertera adalah basis assessment; pasar regional dapat berbeda dari pelabuhan tujuan.')
        else:
            st.caption("Assessment CFR tujuan belum tersedia dalam laporan.")
        regional = argus["regional_fob"].get(country) if argus else None
        if regional:
            st.markdown("**Konteks regional: harga FOB asal**")
            st.write(f'Argus · {regional["label"]} · USD {fmt(regional["low"])}–{fmt(regional["high"])}/MT')
            st.caption(f'FOB North Africa, bukan CFR tujuan · {regional["date"]} · halaman {regional["page"]}')
        elif not entries:
            references = []
            for publisher, source in (("Fertecon", data), ("Argus", argus)):
                record = source.get('global_fob') if source else None
                if record:
                    references.append({"Sumber": publisher, "Pasar": record['label'],
                        "USD/MT": fmt(record['low']) + '–' + fmt(record['high']),
                        "Tanggal": record['date'], "Halaman": record['page']})
            if references:
                st.markdown('**Konteks pasar global: FOB Asia Tenggara**')
                st.dataframe(references, hide_index=True, width='stretch')
                st.caption('Assessment FOB Asia Tenggara; wilayah dan basis dapat berbeda dari tujuan kasus.')
    with b:
        st.markdown("**Freight comparable voyage**")
        matches = voyage_matches(data["voyages"], values["loading_port"], values["discharging_port"]) if data else []
        if not matches:
            st.caption("Rute pembanding yang cukup cocok belum tersedia.")
        else:
            matches = sorted(matches, key=lambda r: abs(r["cargo_mt"] - float(values["cargo_mt"])))[:3]
            scope_labels = {'rute_kawasan': 'Rute kawasan',
                'tujuan_kawasan_asal_berbeda': 'Tujuan kawasan; asal berbeda',
                'asal_kawasan_tujuan_berbeda': 'Asal kawasan; tujuan berbeda',
                'rute_global_berbeda': 'Konteks global; asal dan tujuan berbeda'}
            st.dataframe([{"Rute pembanding": r["origin"] + " → " + r["destination"],
                "Muatan (MT)": fmt(r["cargo_mt"]), "Freight (USD/MT)": fmt(r["low"]) + "–" + fmt(r["high"]),
                "Cakupan": scope_labels[r["match_scope"]],
                "Selisih indikasi vs rentang (USD/MT)": "—" if r["match_scope"] != "rute_kawasan" else
                    " s.d. ".join(fmt(x) for x in comparison_delta(report["pricing"]["computed_freight_usd_mt"], r)),
                "Tanggal": r["date"]} for r in matches], hide_index=True, width="stretch")
            st.caption("Fertecon · halaman 2. Asal, tujuan dan tonase pembanding dapat berbeda dari kasus.")
    if not data and not argus:
        st.warning("Laporan pembanding belum dapat dibaca.")
    st.caption("Harga laporan bersifat historis; bukan penawaran freight untuk rute ini.")


def voyage_view(case, root, output_root, editing):
    section("02", "Voyage Economics")
    profile = case.context["vessel_profile"]
    values = case.current_values()
    profiles = active_catalog(root)
    from decimal import Decimal, InvalidOperation
    try:
        over_capacity = Decimal(str(values['cargo_mt'])) > Decimal(str(values['dwt_mt']))
    except (InvalidOperation, ValueError):
        over_capacity = False
    if over_capacity:
        st.error('Muatan melebihi DWT kapal. Kurangi muatan atau pilih kapal lain.')
    from pilog_cfr_dss.calculations.capacity import deadweight_headroom_mt, gross_dwt_screen
    capacity_invalid = False
    try:
        if case.context.get('capacity_basis') == 'dataset_allowances_v1':
            capacity_invalid = deadweight_headroom_mt(Decimal(values['dwt_mt']), Decimal(values['bunkers_allowance_mt']),
                Decimal(values['constants_allowance_mt']), Decimal(values['cargo_mt'])) < 0
            if capacity_invalid and not over_capacity:
                st.error('Cargo melebihi sisa kapasitas setelah allowance bunker dan constants. Periksa muatan dan allowance.')
        bounds = case.context['vessel_policy'][values['vessel_class']]
        class_ok, class_reason = gross_dwt_screen(Decimal(values['dwt_mt']), Decimal(values['cargo_mt']), Decimal(str(bounds[0])), Decimal(str(bounds[1])))
        if not class_ok and class_reason == 'CASE_VESSEL_OUTSIDE_CLASS_RANGE':
            st.error('DWT tidak sesuai rentang kebijakan kelas kapal terpilih. Periksa DWT atau pilih kelas lain.')
            capacity_invalid = True
    except (ValueError, KeyError, InvalidOperation):
        capacity_invalid = True
    left, right = st.columns([1, 2])
    error_key = "voyage_error_" + case.draft_id
    if st.session_state.get(error_key + '_basis') != case.fingerprint:
        st.session_state.pop(error_key, None)
    if st.session_state.get(error_key):
        error = st.session_state[error_key]
        st.error('Muatan melebihi DWT kapal. Kurangi muatan atau pilih kapal lain.' if error == 'CARGO_EXCEEDS_CASE_GROSS_DWT' else 'Voyage belum dapat dihitung: ' + error)
    with left:
        if st.button("Hitung ekonomi voyage", type="primary", disabled=editing or over_capacity or capacity_invalid, width="stretch"):
            try:
                with st.spinner("Menghitung durasi, biaya dan tarif…"):
                    case.prepare(output_root / "ui_cases")
                st.session_state.pop(error_key, None)
                st.rerun()
            except (ValueError, TypeError, KeyError, OSError, ArithmeticError) as error:
                st.session_state[error_key] = str(error)
                st.session_state[error_key + '_basis'] = case.fingerprint
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
        return
    base, pricing = report["baseline"], report["pricing"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Durasi voyage (hari)", fmt(base["total_days"]))
    c2.metric("Biaya voyage (USD)", fmt(base["total_cash_cost_usd"]))
    c3.metric("Indikasi freight (USD/MT)", fmt(pricing["computed_freight_usd_mt"]))
    c4.metric("Freight tetap (USD/MT)" if case.fixed else "Estimasi surplus/defisit voyage PILOG (USD)", fmt(pricing["freight_tender_usd_mt"]) if case.fixed else fmt(base["contribution_usd"]))
    tce_actual, breakeven = st.columns(2)
    tce_actual.metric("TCE hasil voyage (USD/hari)", fmt(base["tce_before_running_usd_day"]))
    breakeven.metric("Freight impas (USD/MT)", fmt(report["metrics"]["freight_break_even_usd_mt"], minimum=True))
    st.caption("Surplus dihitung pada freight indikasi yang memenuhi TC Rates; belum membuktikan harga diterima buyer. TCE sebelum biaya operasional kapal.")
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
        st.markdown("**Biaya & estimasi surplus/defisit voyage PILOG**")
        st.dataframe([{"Komponen": title, "USD": fmt(base[key])} for title, key in (
            ("Fuel oil", "fo_cost_usd"), ("Diesel oil", "do_cost_usd"),
            ("Total bahan bakar", "bunker_usd"), ("Pelabuhan dan biaya lain", "port_other_usd"),
            ("Operasional kapal", "running_usd"), ("Komisi", "commission_usd"),
            ("Pendapatan freight", "revenue_usd"), ("Estimasi surplus/defisit voyage PILOG", "contribution_usd"))],
            hide_index=True, width="stretch")
    market_comparables_view(case, root, report)
    with st.expander('Pembebanan biaya & kapasitas'):
        d = report.get('pricing_diagnostics', {})
        st.caption('Seluruh biaya satu voyage dibebankan ke cargo kasus. Satu arah bermuatan; kapasitas berbasis allowance belum membuktikan draft dan ruang muat aktual.')
        st.dataframe([{'Komponen': title, 'Nilai': fmt(d.get(key)), 'Satuan': unit} for title, key, unit in (
            ('Cargo / gross DWT', 'cargo_to_gross_dwt_percent', '%'),
            ('Kapasitas cargo setelah allowance', 'cargo_capacity_after_allowances_mt', 'MT'),
            ('Sisa kapasitas setelah cargo', 'capacity_headroom_mt', 'MT'),
            ('Bunker per MT cargo', 'bunker_per_mt_usd', 'USD/MT'),
            ('Pelabuhan dan lainnya per MT cargo', 'port_other_per_mt_usd', 'USD/MT'),
            ('Operasional kapal per MT cargo', 'running_per_mt_usd', 'USD/MT'))], hide_index=True, width='stretch')
    with st.expander('Sensitivitas biaya — freight baseline tetap'):
        st.caption('Skenario dari parameter kasus; freight tidak dihitung ulang saat biaya atau waktu berubah.')
        st.dataframe([{'Skenario': row['label'], 'Freight (USD/MT)': fmt(row['economics']['freight_usd_mt']),
                       'Biaya voyage (USD)': fmt(row['economics']['total_cash_cost_usd']),
                       'TCE (USD/hari)': fmt(row['economics']['tce_before_running_usd_day']),
                       'Surplus/defisit (USD)': fmt(row['economics']['contribution_usd']),
                       'Perubahan surplus (USD)': fmt(row['change_from_baseline_usd'])}
                      for row in report.get('fixed_freight_sensitivities', [])], hide_index=True, width='stretch')
    with st.expander("Dasar perhitungan"):
        st.markdown(
            "- Hari laut: jarak ÷ kecepatan profil kapal ÷ 24.\n"
            "- Kebutuhan bahan bakar: konsumsi profil kapal × durasi yang sesuai.\n"
            "- Biaya fuel oil/diesel oil: kebutuhan masing-masing × harga bunker yang dipakai di Step 1.\n"
            "- Indikasi freight: biaya pelayaran + target harian × total hari, dibagi muatan; komisi 0%.\n"
            "- Estimasi Surplus PILOG: pendapatan freight dikurangi biaya voyage dan komisi.")
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
            st.dataframe([{"Skenario": row["label"], "Estimasi Surplus PILOG (USD)": fmt(row["economics"]["contribution_usd"]),
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
        try:
            st.session_state["available_market"] = _fresh_market()
        except Exception:
            st.session_state["available_market"] = latest_saved(root, output_root / 'market_cache')
            st.session_state['market_offline'] = True
        if st.session_state.get('available_market'):
            try:
                save_runtime_snapshot(st.session_state['available_market'], output_root / 'market_cache')
            except (ValueError, OSError):
                st.session_state['market_cache_unavailable'] = True
    if not st.session_state["available_market"]:
        st.error("Belum ada snapshot Fearnpulse. Jalankan scripts/refresh_market_inputs.py terlebih dahulu.")
        return
    if st.session_state.get('market_offline'):
        st.caption('Data pasar terakhir tersedia digunakan.')
    if "case" not in st.session_state:
        fresh = new_market_case(root, st.session_state["available_market"], dynamic_route=True)
        try:
            fresh.context['baltic_source'] = _baltic_check()
        except (ValueError, OSError):
            fresh.context['baltic_source'] = {'url':'https://www.balticexchange.com/en/data-services/market-information0/dry-services.html',
                                               'source_status':'reference_checked_2026-11-03', 'live_verified':False}
        choices = ports(root / 'data/raw/Ports.xlsx')
        origin = next((p for p in choices if p[0] == fresh.values()['loading_port']), None)
        dest = next((p for p in choices if p[0] == fresh.values()['discharging_port']), None)
        if origin and dest:
            try:
                ref = distance(origin, dest, root / 'data/raw/Simulasi Tarif Internasional_Mei 2025.xlsx')
                apply_route(fresh, origin, dest, ref)
            except (ValueError, OSError):
                st.session_state['route_failure_' + fresh.draft_id] = (origin, dest)
                fresh.context['case_basis_version'] = 'I5-ROUTE.1'
        else:
            st.error('Pelabuhan default tidak ditemukan di daftar pelabuhan.')
            return
        profiles = active_catalog(root)
        apply_profile(fresh, profiles['profiles'][0], profiles['policy'])
        try:
            fresh.context['market_index'] = read_reports(root)
        except Exception:
            st.warning('Laporan indeks belum terbaca; menggunakan data terakhir yang tersedia.')
        st.session_state["case"] = fresh
    case = st.session_state["case"]
    if not case.fixed and case.context.get('capacity_basis') != 'dataset_allowances_v1':
        case.context['capacity_basis'] = 'dataset_allowances_v1'
        case.context['cost_allocation_basis'] = 'entire_modelled_voyage_to_case_cargo'
        case._invalidate(voyage=True)
    sidebar(root, case, output_root)
    if case.context.get('distance_reference', {}).get('source_status') in {'observed_workbook_distance', 'pending_route'}:
        if case.fixed:
            st.warning('Draft ini memakai jarak OD lama. Buat kasus baru untuk menghitung jarak terbaru.')
            return
        choices = ports(root / 'data/raw/Ports.xlsx')
        origin = next((p for p in choices if p[0] == case.values()['loading_port']), None)
        dest = next((p for p in choices if p[0] == case.values()['discharging_port']), None)
        if origin and dest:
            try:
                ref = distance(origin, dest, root / 'data/raw/Simulasi Tarif Internasional_Mei 2025.xlsx')
                apply_route(case, origin, dest, ref)
                st.rerun()
            except (ValueError, OSError):
                st.session_state['route_failure_' + case.draft_id] = (origin, dest)
                case.context['case_basis_version'] = 'I5-ROUTE.1'
        else:
            st.error('Pelabuhan draft tidak ditemukan di daftar pelabuhan.')
            return
    if case.context.get('case_basis_version') != 'I5-ROUTE.1':
        st.warning('Draft lama memakai basis sebelumnya. Buat kasus baru untuk memakai input saat ini.')
        return
    if not case.context.get("market_snapshot") or case.context.get("case_basis_version") not in (BASIS_VERSION, 'I5-ROUTE.1'):
        st.warning("Draft lama. Buat salinan dengan komisi 0% dan jarak OD; freight serta bid lama tidak diubah.")
        if st.button("Salin dengan basis terbaru"):
            st.session_state["case"] = new_market_case(root, st.session_state["available_market"])
            st.rerun()
        return
    st.html('<header class="workspace-header"><h1>CFR Decision Workspace</h1></header>')
    st.html('<nav class="workflow-strip" aria-label="Alur analisis">'
            '<a href="#pilog-step-01" target="_self"><strong>01</strong>Data & kapal</a>'
            '<a href="#pilog-step-02" target="_self"><strong>02</strong>Voyage Economics</a></nav>')
    section("01", "Data Pengiriman & Kapal")
    prior_editing = any(st.session_state.get(prefix + case.draft_id, False)
        for prefix in ("edit_input_", "edit_cost_", "edit_tender_"))
    pending_route = review_data(case, root, prior_editing)
    editing = input_editor(case, pending_route)
    cost_was_editing = st.session_state.get("edit_cost_" + case.draft_id, False)
    bid_was_editing = st.session_state.get("edit_tender_" + case.draft_id, False)
    voyage_view(case, root, output_root, editing or cost_was_editing or bool(pending_route))
