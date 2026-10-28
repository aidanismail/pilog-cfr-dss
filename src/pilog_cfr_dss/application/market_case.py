"""Compose a case from a workbook profile and a captured market snapshot."""
from copy import deepcopy
from datetime import timedelta
import json
from pathlib import Path

from pilog_cfr_dss.application.interactive_case import InteractiveCase
from pilog_cfr_dss.models.tender_clock import round_window
from pilog_cfr_dss.orchestration.price_records import utc_now
from pilog_cfr_dss.validation.iteration_04 import timestamp
from pilog_cfr_dss.sources.od_distance import read_distance
from pilog_cfr_dss.validation.case_basis import BASIS_VERSION, COMMISSION_KEYS
from pilog_cfr_dss.validation.cost_forecast import REVIEW_VERSION
from pilog_cfr_dss.validation.iteration_04 import number
from pilog_cfr_dss.calculations.pricing_04 import economics
from pilog_cfr_dss.calculations.commercial_review import net_daily, demo_port_cost
from pilog_cfr_dss.calculations.capacity import gross_dwt_screen
from decimal import localcontext


def catalog(root: Path) -> dict:
    return json.loads((root / "data/processed/vessel_profiles_i4.json").read_text(encoding="utf-8"))


def apply_case_basis(case: InteractiveCase, root: Path) -> None:
    """Apply the approved zero-commission/distance-only basis to an unfixed revision."""
    if case.fixed:
        raise ValueError("BASIS_FIXED_CREATE_REVISION")
    values = case.values()
    distance = read_distance(root / "docs/it_4/Simulasi Tarif Internasional_Mei 2025.xlsx",
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


def apply_profile(case: InteractiveCase, profile: dict, policy: dict) -> None:
    if case.fixed:
        raise ValueError("BASIS_FIXED_CREATE_REVISION")
    fields = {**profile["fields"], "vessel_class": profile["vessel_class"]}
    for row in case.rows:
        if row["key"] in fields:
            key = row["key"]
            row.update(value=fields[key], source_status="observed_workbook_profile_transfer",
                source_reference=profile["source_reference"] + " :: " + profile["sheet"] + "!" + profile["source_cells"].get(key, "C16"),
                note=profile["note"])
    case.context["vessel_profile"] = deepcopy(profile)
    case.context["vessel_policy"] = deepcopy(policy)
    case._invalidate(voyage=True)
    if case.context.get("market_snapshot"):
        apply_market(case, case.context["market_snapshot"])


def apply_market(case: InteractiveCase, snapshot: dict) -> None:
    if case.fixed:
        raise ValueError("BASIS_FIXED_CREATE_REVISION")
    snapshot = deepcopy(snapshot)
    profile = case.context["vessel_profile"]
    target = deepcopy(snapshot["tc_rates"][profile["market_family"]])
    target.update(source_snapshot_id=snapshot["snapshot_id"], source_fetched_at=snapshot["fetched_at"],
        mapping_basis="1-year TC as target TCE; assumed net before running; owned mode, no hire expense",
        class_proxy=profile["market_class_proxy"])
    if profile["market_class_proxy"]:
        target["source_status"] = "observed_market_with_class_proxy"
        target["note"] = "Handymax 47.175 DWT memakai acuan kelompok kecil Handysize 38k; bukan quote khusus Handymax."
    case.context["market_snapshot"] = snapshot
    case.context["pricing"]["target_tce"] = target
    case.context["market_sources"] = {"fearnpulse": {"snapshot_id": snapshot["snapshot_id"], "url": snapshot["url"],
        "fetched_at": snapshot["fetched_at"], "report_published_at": snapshot["report_published_at"]}}
    for row in case.rows:
        if row["key"] in snapshot["bunkers"]:
            quote = snapshot["bunkers"][row["key"]]
            row.update(value=quote["value"], source_status=quote["source_status"],
                source_reference=quote["source_reference"],
                note="Observasi " + quote["source_observed_on"] + "; benchmark Singapore, bukan bukti pembelian bunker aktual.")
    case._invalidate(voyage=True)


def new_market_case(root: Path, snapshot: dict, profile_id: str | None = None) -> InteractiveCase:
    case = InteractiveCase.read(root / "data/processed/i4_context.json").revise()
    profiles = catalog(root)
    profile = next((p for p in profiles["profiles"] if p["profile_id"] == (profile_id or "ve_sheet1")), None)
    if profile is None:
        raise ValueError("UNKNOWN_WORKBOOK_PROFILE")
    case.context.pop("market_sources", None)
    case.context["limitations"] = [
        "Spesifikasi workbook ditransfer ke kasus urea Bontang-Mundra; bukan bukti kapal tersedia.",
        "OD hanya sumber jarak satu arah dalam NM; bukan sumber tarif freight atau biaya.",
        "Jarak OD belum verifikasi navigasi independen; biaya pelabuhan masih transfer template.",
        "1-year T/C dipakai sebagai target TCE net simulasi; basis komisi sumber tidak dinyatakan. Tidak ada hire cost tambahan.",
        "Tanggal observasi setiap seri dapat berbeda; waktu fetch bukan waktu harga pasar.",
        "Gross DWT belum membuktikan DWCC, terminal, laycan atau availability.",
    ]
    apply_profile(case, profile, profiles["policy"])
    apply_market(case, snapshot)
    apply_case_basis(case, root)
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
    name = "i4_no_go.json" if no_go else "i4_context.json"
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
        from pilog_cfr_dss.orchestration.iteration_04 import serial
        results.append({"profile_id": profile["profile_id"], "sheet": profile["sheet"],
            "vessel_class": profile["vessel_class"], "dwt_mt": profile["fields"]["dwt_mt"],
            "market_series": candidate.context["pricing"]["target_tce"]["series"],
            "class_proxy": profile["market_class_proxy"], "target_tce_usd_day": candidate.context["pricing"]["target_tce"]["value"],
            "baseline": report["baseline"], "computed_freight_usd_mt": report["pricing"]["computed_freight_usd_mt"],
            "calculated_at": report["calculated_at"], "common_freight_usd_mt": str(rate),
            "common_rate_economics": serial(common), "common_contribution_per_day_usd": str(daily),
            "capacity_screen_passed": capacity_ok, "automatic_vessel_selection": False})
    return results


def demo_case(root: Path, snapshot: dict, drafts_root: Path, kind: str = "go", profile_id: str | None = None,
              base_case: InteractiveCase | None = None) -> InteractiveCase:
    if kind not in {"go", "no-go-floor", "no-go-economics"}:
        raise ValueError("UNKNOWN_DEMONSTRATION_CASE")
    case = (InteractiveCase(deepcopy(base_case.context), deepcopy(base_case.rows)) if base_case is not None
            else new_market_case(root, snapshot, profile_id))
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
