"""Compose a case from a workbook profile and a captured market snapshot."""
from copy import deepcopy
from functools import lru_cache
import hashlib
from datetime import timedelta
import json
from pathlib import Path

from pilog_cfr_dss.application.interactive_case import InteractiveCase
from pilog_cfr_dss.models.tender_clock import round_window
from pilog_cfr_dss.orchestration.price_records import utc_now
from pilog_cfr_dss.validation.case import timestamp
from pilog_cfr_dss.sources.od_distance import read_distance
from pilog_cfr_dss.validation.case_basis import BASIS_VERSION, COMMISSION_KEYS
from pilog_cfr_dss.validation.case_basis import ROUTE_VERSION
from pilog_cfr_dss.validation.cost_forecast import REVIEW_VERSION
from pilog_cfr_dss.validation.case import number
from pilog_cfr_dss.calculations.freight_pricing import economics
from pilog_cfr_dss.calculations.commercial_review import net_daily, demo_port_cost
from pilog_cfr_dss.calculations.capacity import gross_dwt_screen
from decimal import localcontext
from pilog_cfr_dss.sources.voyage_profiles import read_profiles
from pilog_cfr_dss.sources.voyage_estimates import read_voyages
from pilog_cfr_dss.models.case import CHARTER_VERSION, is_chartered


@lru_cache(maxsize=8)
def _profiles(path: str, digest: str, chartered: bool = False) -> dict:
    result = read_profiles(Path(path), include_owned_running=not chartered)
    if result["source_sha256"] != digest:
        raise ValueError("WORKBOOK_CHANGED_DURING_READ")
    return result


@lru_cache(maxsize=8)
def _voyages(path: str, digest: str, od: str | None, od_digest: str | None) -> dict:
    result = read_voyages(Path(path), Path(od) if od else None)
    if result["source_sha256"] != digest or (od and any(v["distance_reference"]["source_sha256"] != od_digest for v in result["voyages"])):
        raise ValueError("WORKBOOK_CHANGED_DURING_READ")
    return result


def catalog(root: Path, *, chartered: bool = False) -> dict:
    path = root / "data/raw/Voyage Estimate.xlsx"
    return deepcopy(_profiles(str(path.resolve()), hashlib.sha256(path.read_bytes()).hexdigest(), chartered))


def active_catalog(root: Path) -> dict:
    """Two Baltic reference vessels; unspecified values retain workbook defaults."""
    from pilog_cfr_dss.sources.baltic_profiles import read_snapshot
    data = catalog(root, chartered=True)
    snapshot = read_snapshot()
    selected = [next(p for p in data['profiles'] if p['profile_code'] == code) for code in ('HS38', 'SUP58')]
    for p in selected:
        entry=snapshot['profiles'][p['vessel_class']]
        values={key:entry[key] for key in ('dwt_mt','speed_knots','sea_fo_mt_day','sea_do_mt_day')}
        p['fields'].update(values)
        p['baltic_fields'] = list(values)
        p['baltic_source_url']=snapshot['source_url'];p['baltic_page']=entry['page'];p['baltic_version']=snapshot['document_version']
        p['note'] = 'Benchmark Baltic; nilai lain dari workbook, bukan data kapal aktual.'
    data['profiles'] = selected
    data['policy']['Supramax'] = ['50000','63500']
    return data


def voyage_catalog(root: Path, *, dynamic_route: bool = False) -> dict:
    path = root / "data/raw/Voyage Estimate.xlsx"
    if dynamic_route:
        return deepcopy(_voyages(str(path.resolve()), hashlib.sha256(path.read_bytes()).hexdigest(), None, None))
    od = root / "data/raw/Simulasi Tarif Internasional_Mei 2025.xlsx"
    return deepcopy(_voyages(str(path.resolve()), hashlib.sha256(path.read_bytes()).hexdigest(),
                             str(od.resolve()), hashlib.sha256(od.read_bytes()).hexdigest()))


def apply_voyage(case: InteractiveCase, voyage: dict, root: Path, *, dynamic_route: bool = False) -> None:
    if case.fixed:
        raise ValueError("BASIS_FIXED_CREATE_REVISION")
    for row in case.rows:
        if row["key"] in voyage["fields"]:
            row.update(value=voyage["fields"][row["key"]], source_status=voyage["source_status"],
                       source_reference=voyage["source_reference"] + " :: " + voyage["sheet"] + "!" + voyage["source_cells"][row["key"]],
                       note=voyage["note"])
    case.context["voyage_estimate"] = deepcopy(voyage)
    case.context.setdefault("source_manifest", {})[voyage["source_reference"]] = voyage["source_sha256"]
    case.context.pop("pi_selected_bid_id", None)
    case.context.pop("demonstration", None)
    case.context["bids"] = []
    if dynamic_route:
        for row in case.rows:
            if row['key'] in COMMISSION_KEYS:
                row.update(value='0', source_status='approved_case_policy', source_reference='Komisi kasus aktif 0%')
            if row['key'] == 'distance_nm':
                row.update(value='', source_status='pending_route', source_reference='Jarak menunggu rute laut atau input manual')
        case.context.update(case_basis_version=ROUTE_VERSION, od_usage='distance_only', distance_reference={
            'source_status': 'pending_route', 'unit': 'NM', 'loading_port': voyage['fields']['loading_port'],
            'discharging_port': voyage['fields']['discharging_port'], 'value': ''})
        case.context['capacity_basis'] = 'dataset_allowances_v1'
        case.context['cost_allocation_basis'] = 'entire_modelled_voyage_to_case_cargo'
        case.context['limitations'] = [
            'Satu arah bermuatan; seluruh biaya model dibebankan ke cargo kasus.',
            'Jarak laut estimasi; bukan bukti rute navigasi atau kesiapan terminal.',
            'Default handling, tunggu, biaya pelabuhan dan sebagian profil berasal dari workbook.',
            'TC Rates menjadi acuan freight indikatif; Hire/day terpisah dan bukan quote kapal aktual.',
            'Kapasitas memakai allowance dataset; belum membuktikan draft atau ruang muat aktual.',
        ]
        case.context.pop('od_reference', None)
        case._invalidate(voyage=True)
    else:
        apply_case_basis(case, root)


def apply_case_basis(case: InteractiveCase, root: Path) -> None:
    """Apply the approved zero-commission/distance-only basis to an unfixed revision."""
    if case.fixed:
        raise ValueError("BASIS_FIXED_CREATE_REVISION")
    values = case.values()
    distance = read_distance(root / "data/raw/Simulasi Tarif Internasional_Mei 2025.xlsx",
                             values["loading_port"], values["discharging_port"], values["cargo_description"])
    for row in case.rows:
        if row["key"] in COMMISSION_KEYS:
            row.update(value="0", source_status="approved_case_policy",
                       source_reference="D-061/D-062: all three commissions 0%",
                       note="Komisi 0% untuk kasus aktif; histori sumber tidak diubah.")
        elif row["key"] == "distance_nm":
            row.update(value=distance["value"], source_status=distance["source_status"],
                       source_reference=distance["source_reference"],
                       note="Jarak satu arah dalam NM dari OD; belum verifikasi navigasi independen.")
    case.context.pop("od_reference", None)
    case.context.pop("od_reference_valid", None)
    case.context.update(case_basis_version=BASIS_VERSION, od_usage="distance_only", distance_reference=distance)
    case._invalidate(voyage=True)


def apply_route(case: InteractiveCase, origin: tuple, destination: tuple, reference: dict) -> None:
    """Install one explicitly resolved route on an editable case."""
    if case.fixed:
        raise ValueError('BASIS_FIXED_CREATE_REVISION')
    if origin == destination or reference.get('loading_port') != origin[0] or reference.get('discharging_port') != destination[0]:
        raise ValueError('ROUTE_DISTANCE_ROUTE_MISMATCH')
    if number(reference['value'], 'distance_nm') <= 0:
        raise ValueError('INVALID_ROUTE_DISTANCE')
    fields = {'loading_port': origin[0], 'discharging_port': destination[0], 'distance_nm': str(reference['value'])}
    for row in case.rows:
        if row['key'] in fields:
            row.update(value=fields[row['key']], source_status=reference['source_status'],
                       source_reference=reference['source_reference'], note='Rute dipilih pengguna.')
    case.context.update(case_basis_version=ROUTE_VERSION, od_usage='distance_only', distance_reference=deepcopy(reference),
                        route_countries={'loading':origin[1], 'discharging':destination[1]})
    case.context.pop('od_reference', None); case.context.pop('od_reference_valid', None)
    case.context['bids'] = []; case.context.pop('pi_selected_bid_id', None)
    case._invalidate(voyage=True)


def apply_profile(case: InteractiveCase, profile: dict, policy: dict) -> None:
    if case.fixed:
        raise ValueError("BASIS_FIXED_CREATE_REVISION")
    fields = {**profile["fields"], "vessel_class": profile["vessel_class"]}
    for row in case.rows:
        if row["key"] in fields:
            key = row["key"]
            row.update(value=fields[key], source_status=('observed_reference' if key in profile.get('baltic_fields', []) else profile.get("source_status", "observed_workbook_profile_transfer")),
                source_reference=(profile['baltic_source_url'] + ' :: page ' + str(profile['baltic_page']) if key in profile.get('baltic_fields', []) else profile["source_reference"] + " :: " + profile["sheet"] + "!" + profile["source_cells"].get(key, "C16")),
                note=profile["note"])
    case.context["vessel_profile"] = deepcopy(profile)
    case.context["vessel_policy"] = deepcopy(policy)
    case._invalidate(voyage=True)
    if case.context.get("market_snapshot"):
        apply_market(case, case.context["market_snapshot"], preserve_manual=True)


def apply_market(case: InteractiveCase, snapshot: dict, *, preserve_manual: bool = False) -> None:
    if case.fixed:
        raise ValueError("BASIS_FIXED_CREATE_REVISION")
    snapshot = deepcopy(snapshot)
    profile = case.context["vessel_profile"]
    target = deepcopy(snapshot["tc_rates"][profile["market_family"]])
    target.update(source_snapshot_id=snapshot["snapshot_id"], source_fetched_at=snapshot["fetched_at"],
        mapping_basis=("Class TC reference for indicative freight; charter hire is a separate case input"
                       if is_chartered(case.context) else
                       "1-year TC as target TCE; assumed net before running; owned mode, no hire expense"),
        class_proxy=profile["market_class_proxy"])
    if profile["market_class_proxy"]:
        target["source_status"] = "observed_market_with_class_proxy"
        target["note"] = "Handymax memakai acuan kelompok kecil Handysize 38k; bukan quote khusus Handymax."
    case.context["market_snapshot"] = snapshot
    existing_target = case.context["pricing"].get("target_tce", {})
    if not (preserve_manual and existing_target.get("source_status") == "simulation_only_user_input"):
        case.context["pricing"]["target_tce"] = target
    case.context["market_sources"] = {"fearnpulse": {"snapshot_id": snapshot["snapshot_id"], "url": snapshot["url"],
        "fetched_at": snapshot["fetched_at"], "report_published_at": snapshot["report_published_at"]}}
    for row in case.rows:
        if row["key"] in snapshot["bunkers"]:
            if preserve_manual and row.get("source_status") == "simulation_only_user_input":
                continue
            quote = snapshot["bunkers"][row["key"]]
            row.update(value=quote["value"], source_status=quote["source_status"],
                source_reference=quote["source_reference"],
                note="Observasi " + quote["source_observed_on"] + "; benchmark Singapore, bukan bukti pembelian bunker aktual.")
    case._invalidate(voyage=True)


def new_market_case(root: Path, snapshot: dict, profile_id: str | None = None,
                    voyage_id: str | None = None, *, dynamic_route: bool = False) -> InteractiveCase:
    case = InteractiveCase.read(root / "data/processed/case_template.json").revise()
    if dynamic_route:
        # New versioned basis, not a rename of the owned daily-cost value.
        case.context['schema_version'] = CHARTER_VERSION
        case.context['cost_model_version'] = CHARTER_VERSION
        case.context['pricing']['basis'] = 'tce_net_voyage_before_hire'
        case.rows = [row for row in case.rows if row['key'] != 'running_usd_day']
        for row in case.rows:
            if row['key'] == 'vessel_mode':
                row.update(value='chartered', source_status='approved_case_policy',
                           source_reference='Kapal sewa sesuai keputusan pengguna')
        case.rows.append({'key': 'hire_usd_day', 'value': '13000', 'unit': 'USD/day',
                          'source_status': 'approved_historical_hire_default',
                          'source_reference': 'Voyage_Estimate_all_sheets_variable_value_units.xlsx :: AQABA!B66 (sumber historis L38)',
                          'note': 'Default historis disetujui pengguna untuk kedua kelas; editable, bukan quote kapal aktual.',
                          'role': 'input'})
    profiles = active_catalog(root) if dynamic_route else catalog(root)
    profile = next((p for p in profiles["profiles"] if p["profile_id"] == (profile_id or profiles["profiles"][0]["profile_id"])), None)
    if profile is None:
        raise ValueError("UNKNOWN_WORKBOOK_PROFILE")
    voyages = voyage_catalog(root, dynamic_route=dynamic_route)
    voyage = next((v for v in voyages["voyages"] if v["voyage_id"] == (voyage_id or voyages["voyages"][0]["voyage_id"])), None)
    if voyage is None:
        raise ValueError("UNKNOWN_WORKBOOK_VOYAGE")
    case.context.pop("market_sources", None)
    case.context["limitations"] = [
        "Voyage dan profil kapal dipilih terpisah dari workbook; bukan bukti kapal tersedia.",
        "OD hanya sumber jarak satu arah dalam NM; bukan sumber tarif freight atau biaya.",
        "Jarak OD belum verifikasi navigasi independen; muatan/handling/waktu tunggu/biaya pelabuhan adalah asumsi demo.",
        "1-year T/C dipakai sebagai target TCE net simulasi; basis komisi sumber tidak dinyatakan. Tidak ada hire cost tambahan.",
        "Tanggal observasi setiap seri dapat berbeda; waktu fetch bukan waktu harga pasar.",
        "Gross DWT belum membuktikan DWCC, terminal, laycan atau availability.",
    ]
    apply_voyage(case, voyage, root, dynamic_route=dynamic_route)
    apply_profile(case, profile, profiles["policy"])
    apply_market(case, snapshot)
    if dynamic_route:
        case.context['limitations'].append('Hire/day default USD 13.000 merupakan input historis yang disetujui; bukan tarif sewa pasar terkini.')
    case.context["commercial_review_version"] = REVIEW_VERSION
    shocks = case.context["scenarios"]
    fuel = next((s for s in shocks if s["scenario_id"] == "fuel_up"), None)
    delay = next((s for s in shocks if s["scenario_id"] == "port_delay"), None)
    if fuel and delay:
        shocks.append({"scenario_id": "fuel_and_delay", "label": fuel["label"] + " + " + delay["label"],
            "fuel_price_increase_fraction": fuel["fuel_price_increase_fraction"],
            "extra_port_days": delay["extra_port_days"], "source_status": "simulation_only_combined_existing_assumptions"})
    case.context["auction_clock"] = {"mode": "fixed_window", "round_duration_seconds": 180,
        "starts_at": utc_now(), "source_status": "simulation_configured_schedule"}
    case.context["evaluation_cutoff"] = round_window(case.context["auction_clock"], 3)[1].isoformat()
    return case


def seed_demo_bids(case: InteractiveCase, root: Path, *, no_go: bool = False) -> None:
    name = "case_no_go.json" if no_go else "case_template.json"
    bids = json.loads((root / "data/processed" / name).read_text(encoding="utf-8"))["bids"]
    clock = case.context.get("auction_clock")
    if clock:
        for bid in bids:
            opened, _ = round_window(clock, bid["round"])
            bid["submitted_at"] = (opened + timedelta(seconds=30 + bid["sequence"])).isoformat()
        case.context["evaluation_cutoff"] = round_window(clock, max(b["round"] for b in bids))[1].isoformat()
    case.apply_tender(bids, case.context["evaluation_cutoff"])


def compare_profiles(case: InteractiveCase, root: Path, drafts_root: Path, common_freight: str | None = None) -> list[dict]:
    results = []
    profiles = catalog(root)
    if common_freight is None:
        common_freight = case.context["freight_tender"]["value"] if case.fixed else case.revise().prepare(drafts_root)["pricing"]["computed_freight_usd_mt"]
    rate = number(common_freight, "comparison freight")
    if rate < 0:
        raise ValueError("NEGATIVE_COMPARISON_FREIGHT")
    for profile in profiles["profiles"]:
        candidate = case.revise()
        apply_profile(candidate, profile, profiles["policy"])
        report = candidate.prepare(drafts_root)
        with localcontext() as precision:
            precision.prec = 40
            baseline = {k: number(v, k) for k, v in report["baseline"].items()}
            common = economics(baseline, rate, number(candidate.values()["cargo_mt"], "cargo"),
                               number(report["pricing"]["commission_fraction"], "commission"))
            daily = net_daily(common)
        bounds = profiles["policy"][profile["vessel_class"]]
        capacity_ok, _ = gross_dwt_screen(number(profile["fields"]["dwt_mt"], "dwt"), number(candidate.values()["cargo_mt"], "cargo"),
            number(bounds[0], "class min"), number(bounds[1], "class max"))
        from pilog_cfr_dss.orchestration.case_evaluation import serial
        results.append({"profile_id": profile["profile_id"], "sheet": profile["sheet"],
            "profile_code": profile.get("profile_code", profile["profile_id"]),
            "vessel_class": profile["vessel_class"], "dwt_mt": profile["fields"]["dwt_mt"],
            "speed_knots": profile["fields"]["speed_knots"],
            "market_series": candidate.context["pricing"]["target_tce"]["series"],
            "class_proxy": profile["market_class_proxy"], "target_tce_usd_day": candidate.context["pricing"]["target_tce"]["value"],
            "baseline": report["baseline"], "computed_freight_usd_mt": report["pricing"]["computed_freight_usd_mt"],
            "calculated_at": report["calculated_at"], "common_freight_usd_mt": str(rate),
            "common_rate_economics": serial(common), "common_contribution_per_day_usd": str(daily),
            "capacity_screen_passed": capacity_ok, "automatic_vessel_selection": False})
    return results


def demo_case(root: Path, snapshot: dict, drafts_root: Path, kind: str = "go", profile_id: str | None = None,
              base_case: InteractiveCase | None = None, voyage_id: str | None = None) -> InteractiveCase:
    if kind not in {"go", "no-go-floor", "no-go-economics"}:
        raise ValueError("UNKNOWN_DEMONSTRATION_CASE")
    case = (InteractiveCase(deepcopy(base_case.context), deepcopy(base_case.rows)) if base_case is not None
            else new_market_case(root, snapshot, profile_id, voyage_id))
    prepared = case.prepare(drafts_root)
    case.fix_freight(drafts_root)
    seed_demo_bids(case, root, no_go=kind == "no-go-floor")
    if kind == "no-go-economics":
        with localcontext() as precision:
            precision.prec = 40
            cost = demo_port_cost(number(case.values()["port_other_total_usd"], "port"), number(prepared["baseline"]["contribution_usd"], "contribution"))
        case = case.reforecast_costs({"port_other_total_usd": str(cost)},
            "Contoh sintetis NO GO ekonomi: kenaikan estimasi pelabuhan/biaya lain; bukan biaya aktual workbook.")
    case.context["demonstration"] = {"kind": kind, "source_status": "simulation_only_synthetic_workflow_example"}
    return case
