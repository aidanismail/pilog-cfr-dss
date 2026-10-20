"""Versioned post-tender I3 simulation; I2 orchestration remains unchanged."""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pilog_cfr_dss.calculations.tender import market_index, owned_voyage_economics, tender_bids
from pilog_cfr_dss.decisions.iteration_03 import evaluate_cfr_gates
from pilog_cfr_dss.reporting.iteration_03 import render_i3_brief
from pilog_cfr_dss.validation.iteration_03 import decimal, load_case, validate_commercial_fixture


FORMULA_VERSION = "I3.1"
RULE_VERSION = "I3.1"
DEFAULT_VESSEL_POLICY = Path(__file__).resolve().parents[3] / "data" / "processed" / "vessel_classes.json"


def evaluate(case_path: Path, vessel_policy_path: Path = DEFAULT_VESSEL_POLICY) -> dict[str, Any]:
    """The only public actions are GO and NO_GO. Bad evidence is NO_GO/DATA_ISSUE."""
    report: dict[str, Any] = {
        "case_id": case_path.stem, "mode": "simulation", "status": "advisory-only",
        "formula_version": FORMULA_VERSION, "rule_version": RULE_VERSION,
        "recommendation": {"action": "NO_GO", "reason_category": "DATA_ISSUE", "reason_codes": [],
                           "human_approval_required": True, "approval_status": "PENDING_HUMAN_REVIEW"},
    }
    try:
        case, fixture, _ = load_case(case_path)
        report["case_id"] = case.case_id
        report["dataset_sha256"] = case.dataset_sha256
        report["case_fixture_sha256"] = case.manual_sha256
        report["vessel_policy_sha256"] = hashlib.sha256(vessel_policy_path.read_bytes()).hexdigest()
        validate_commercial_fixture(fixture)
        policy = json.loads(vessel_policy_path.read_text(encoding="utf-8"))
        index, index_trace = market_index(fixture)
        oe = decimal(fixture["oe_hps"]["value"], "oe_hps")
        bids = tender_bids(index, oe, fixture["bids"])
        economics, physical = owned_voyage_economics(case)
        od_proxy = decimal(economics["derived_od_cost_proxy_usd_mt"], "derived_od_proxy")
        q = case.number("dwcc_cargo_quantity_mt")
        for bid in bids:
            cfr = decimal(bid["fob_usd_mt"], "fob") + od_proxy
            bid["cfr_usd_mt"] = str(cfr)
            bid["buyer_cfr_total_usd"] = str(cfr * q)
        decision = evaluate_cfr_gates(case, fixture, bids, economics, policy)
        selected = next((bid for bid in bids if bid["bid_id"] == decision.get("selected_bid_id")), None)
        report.update({
            "route": {"origin": case.origin, "destination": case.destination},
            "commodity": str(case.values["cargo_description"]), "cargo_mt": str(q),
            "tender": {"index": index_trace, "oe_hps_usd_mt": str(oe),
                       "oe_hps_source_status": fixture["oe_hps"]["source_status"],
                       "bids": bids, "pi_selected_bid_id": fixture["pi_selected_bid"]["bid_id"]},
            "economics": economics, "physical_trace": physical,
            "selected_bid": selected,
            "gates": {key: value for key, value in decision.items() if key not in {"action", "next_action"}},
            "input_lineage": {
                "voyage_fields": {key: {"value": row["value"], "unit": row["unit"],
                                        "source_status": row["source_status"],
                                        "source_reference": row["source_reference"]}
                                  for key, row in case.raw_rows.items()},
                "non_dataset_fields": {
                    "market_index": fixture["market_index"], "oe_hps": fixture["oe_hps"],
                    "bids": fixture["bids"], "pi_selected_bid": fixture["pi_selected_bid"],
                    "economic_assumptions": fixture["economic_assumptions"],
                },
            },
            "limitations": [
                "Semua harga indeks, OE/HPS, alpha, buyer, dan pilihan kandidat dalam fixture ini sintetis; bukan penawaran aktual.",
                "Rute Bontang–ECI dan banyak input voyage diwarisi dari data eksperimen, belum diverifikasi sebagai shipment urea.",
                "OD cost menggunakan proxy total biaya voyage/45.000 MT, bukan OD cost matrix resmi.",
                "Tarif jual PILOG 20 USD/MT diwarisi dari I2; kontrak PI–PILOG I3 dan basis komisi belum terkonfirmasi.",
                "Screen kapal hanya DWT awal dan allowance; DWCC aktual, draft, terminal, laycan, availability belum terbukti.",
                "GO berarti layak untuk review manusia, bukan award tender, quotation, persetujuan, atau fixture kapal.",
            ],
        })
        report["recommendation"] = {
            "action": decision["action"], "reason_category": decision["reason_category"],
            "reason_codes": decision["reason_codes"], "next_action": decision["next_action"],
            "human_approval_required": True, "approval_status": "PENDING_HUMAN_REVIEW",
        }
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as error:
        report["recommendation"] = {
            "action": "NO_GO", "reason_category": "DATA_ISSUE",
            "reason_codes": [f"INPUT_OR_CALCULATION_ERROR:{error}"],
            "next_action": "Perbaiki/konfirmasi input dan jalankan ulang; ini bukan penolakan komersial terhadap buyer.",
            "human_approval_required": True, "approval_status": "PENDING_HUMAN_REVIEW",
        }
        report["gates"] = {"gate_a": "NOT_EVALUATED", "gate_b": "NOT_EVALUATED"}
    return report


def persist_run(report: dict[str, Any], case_path: Path, output_root: Path,
                vessel_policy_path: Path = DEFAULT_VESSEL_POLICY) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_dir = output_root / f"i3_{stamp}_{case_path.stem}"
    run_dir.mkdir(parents=True, exist_ok=False)
    report = {**report, "run_id": run_dir.name, "generated_at_utc": datetime.now(timezone.utc).isoformat()}
    snapshot_dir = run_dir / "input_snapshot"
    snapshot_dir.mkdir()
    paths = {"case_fixture": case_path, "vessel_policy": vessel_policy_path}
    if case_path.exists():
        try:
            reference = json.loads(case_path.read_text(encoding="utf-8")).get("voyage_dataset")
            if isinstance(reference, str) and Path(reference).name == reference:
                paths["voyage_dataset"] = case_path.parent / reference
        except json.JSONDecodeError:
            pass
    snapshots = {}
    for name, source in paths.items():
        if source.exists() and source.is_file():
            destination = snapshot_dir / f"{name}{source.suffix.lower()}"
            shutil.copyfile(source, destination)
            digest = hashlib.sha256(destination.read_bytes()).hexdigest()
            expected_key = {"case_fixture": "case_fixture_sha256", "voyage_dataset": "dataset_sha256",
                            "vessel_policy": "vessel_policy_sha256"}[name]
            if expected_key in report and digest != report[expected_key]:
                raise ValueError(f"INPUT_CHANGED_DURING_RUN:{name}")
            snapshots[name] = {"file": destination.relative_to(run_dir).as_posix(),
                               "sha256": digest}
    report["input_snapshot"] = snapshots
    (run_dir / "decision_brief.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    (run_dir / "decision_brief.md").write_text(render_i3_brief(report), encoding="utf-8")
    return run_dir
