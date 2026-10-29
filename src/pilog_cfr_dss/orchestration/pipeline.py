from __future__ import annotations

import json
import hashlib
import shutil
from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from pilog_cfr_dss.calculations.physical import calculate_physical
from pilog_cfr_dss.calculations.pricing import fob_usd_mt
from pilog_cfr_dss.decisions.gates import gate_1, gate_2
from pilog_cfr_dss.models.contracts import FORMULA_VERSION, RULE_VERSION, ScenarioEvidence
from pilog_cfr_dss.reporting.brief import render_brief
from pilog_cfr_dss.scenarios.build import build_scenarios
from pilog_cfr_dss.scenarios.economics import enrich_scenarios
from pilog_cfr_dss.validation.ingest import assess_quality, load_snapshot


def _decimal(item: Any) -> Decimal | None:
    try:
        value = Decimal(str(item))
        return value if value.is_finite() else None
    except (InvalidOperation, TypeError, ValueError):
        return None


def _scenario_dict(item: ScenarioEvidence) -> dict[str, Any]:
    return {**asdict(item), "contribution_usd": str(item.contribution_usd) if item.contribution_usd is not None else None, "reasons": list(item.reasons)}


DEFAULT_VESSEL_POLICY = Path(__file__).resolve().parents[3] / "data" / "processed" / "vessel_classes.json"


def evaluate(
    dataset_path: Path, catalog_path: Path, manual_path: Path,
    vessel_policy_path: Path = DEFAULT_VESSEL_POLICY,
) -> dict[str, Any]:
    case = load_snapshot(dataset_path, catalog_path, manual_path)
    quality = assess_quality(case)
    class_policy = json.loads(vessel_policy_path.read_text(encoding="utf-8"))
    pricing = case.manual.get("pricing", {})
    index = _decimal(pricing.get("index", {}).get("value"))
    alpha = _decimal(pricing.get("alpha", {}).get("value"))
    fob = fob_usd_mt(index, alpha) if quality.status != "BLOCK" and index is not None and alpha is not None else None
    gate1 = gate_1(quality, case.manual)
    try:
        physical = calculate_physical(case) if gate1["outcome"] == "CFR_ELIGIBLE" else {
            "status": "NOT_RUN", "results": {},
            "limitations": [f"Gate 1 stopped CFR calculation: {gate1['outcome']}"],
        }
    except ValueError as error:
        physical = {"status": "HOLD_DATA_ISSUE", "results": {}, "limitations": [str(error)]}
    if gate1["outcome"] != "CFR_ELIGIBLE":
        scenarios = (
            ScenarioEvidence(
                "FOB-BASELINE", "FOB", None, None, None, None, None,
                "PRICE_BASELINE_ONLY" if fob is not None else "NOT_CALCULATED",
                ("FOB_PRICE_AVAILABLE_NOT_PROFIT",) if fob is not None else ("MISSING_FOB_PRICE",),
            ),
            ScenarioEvidence(
                "CFR-PILOG", "CFR", None, "PILOG", None, None, None,
                "NOT_RUN_GATE_1", tuple(gate1["reasons"]),
            ),
        )
        vessel_screen: dict[str, Any] = {}
    else:
        scenarios, vessel_screen = build_scenarios(case, fob, class_policy)
    if gate1["outcome"] == "CFR_ELIGIBLE":
        scenarios, scenario_economics = enrich_scenarios(case, scenarios, physical, fob)
    else:
        scenario_economics = {}
    definitions = case.manual.get("economic_definitions", {})
    simulation_assumptions = list(case.manual.get("simulation_assumptions", []))
    gate2 = gate_2(gate1, scenarios, definitions.get("decision_objective"), simulation_assumptions)
    selected_scenario = next((item for item in scenarios if item.scenario_id == gate2.get("selected_scenario_id")), None)
    cfr_scenario = next((item for item in scenarios if item.sales_term == "CFR"), None)
    cfr_detail = scenario_economics.get("CFR-PILOG", {})
    action = gate1["outcome"] if gate1["outcome"] == "HOLD_DATA_ISSUE" else gate2["outcome"]
    reasons = gate1["reasons"] if gate1["outcome"] == "HOLD_DATA_ISSUE" else gate2.get("reason_codes", [])
    report = {
        'scenario_economics': scenario_economics,
        "case_id": case.case_id, "mode": "simulation", "status": "advisory-only",
        "formula_version": FORMULA_VERSION, "rule_version": RULE_VERSION,
        "dataset_sha256": case.dataset_sha256, "catalog_sha256": hashlib.sha256(catalog_path.read_bytes()).hexdigest(),
        "manual_sha256": case.manual_sha256, "vessel_policy_sha256": hashlib.sha256(vessel_policy_path.read_bytes()).hexdigest(),
        "vessel_policy_version": class_policy.get("policy_version"),
        "route": {"origin": case.origin, "destination": case.destination},
        "quantity_basis": {
            "key": "dwcc_cargo_quantity_mt",
            "cargo_mt": str(case.number("dwcc_cargo_quantity_mt")) if quality.status != "BLOCK" else None,
            "applies_to": ["port_days", "dwt_screen", "freight_revenue", "commission", "freight_cost_per_mt"],
        },
        "decision_stage": case.manual.get("decision_stage"),
        "buyer_response": case.manual.get("buyer_response"),
        "contracting_roles": {
            "commodity_seller": case.manual.get("commodity_seller"),
            "freight_provider": case.manual.get("freight_provider"),
        },
        "vessel_class_screen": vessel_screen,
        "vessel_class_selection": {
            "selected_class": selected_scenario.vessel_class if selected_scenario else None,
            "preliminary_candidate_class": cfr_scenario.vessel_class if cfr_scenario else None,
            "selected_scenario_id": gate2.get("selected_scenario_id"),
            "status": gate2["outcome"],
        },
        "simulation_assumptions": simulation_assumptions,
        "quality": {"status": quality.status, "checks": list(quality.checks)},
        "pricing": {
            "fob_usd_mt": str(fob) if fob is not None else None,
            "cfr_indicative_usd_mt": cfr_detail.get("cfr_usd_mt"),
            "index_usd_mt": str(index) if index is not None else None,
            "alpha_usd_mt": str(alpha) if alpha is not None else None,
            "adjustment_usd_mt": cfr_detail.get("cfr_adjustment_usd_mt"),
            "freight_rate_dataset_status": definitions.get("freight_rate_object", "unconfirmed"),
            "fob_commodity_profit_status": "NOT_ASSESSED",
        },
        "calculation_trace": physical,
        "scenarios": [_scenario_dict(item) for item in scenarios],
        "gate_1": gate1, "gate_2": gate2,
        "recommendation": {
            "action": action, "reasons": reasons,
            "next_action": gate2.get("next_action", "Perbaiki input dan jalankan ulang."),
            "human_approval_required": True, "approval_status": "PENDING_HUMAN_REVIEW",
        },
        "unresolved_definitions": [
            "FOB_COMMODITY_COST_AND_MARGIN", "MINIMUM_COMMERCIAL_MARGIN_DEFERRED",
            "COMMISSION_CONTRACT_BASIS", "OTHER_VOYAGE_COST_BREAKDOWN",
            "ACTUAL_VESSEL_AVAILABILITY_AND_SAFE_LOADING",
        ],
    }
    return report


def persist_run(report: dict[str, Any], output_root: Path, input_paths: dict[str, Path] | None = None) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_id = f"i2_{timestamp}_{report['dataset_sha256'][:8]}"
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    report = {**report, "run_id": run_id, "generated_at_utc": datetime.now(timezone.utc).isoformat()}
    if input_paths:
        snapshot_dir = run_dir / "input_snapshot"
        snapshot_dir.mkdir()
        snapshots: dict[str, dict[str, str]] = {}
        for label, source in input_paths.items():
            destination = snapshot_dir / f"{label}{source.suffix.lower()}"
            shutil.copyfile(source, destination)
            digest = hashlib.sha256(destination.read_bytes()).hexdigest()
            if digest != report[f"{label}_sha256"]:
                raise ValueError(f"INPUT_CHANGED_DURING_RUN:{label}")
            snapshots[label] = {"file": destination.relative_to(run_dir).as_posix(), "sha256": digest}
        report["input_snapshot"] = snapshots
    (run_dir / "decision_brief.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    (run_dir / "decision_brief.md").write_text(render_brief(report), encoding="utf-8")
    for name, content in (
        ('scenario_economics.json', report['scenario_economics']),
        ("quality_report.json", report["quality"]),
        ("calculation_trace.json", report["calculation_trace"]),
        ("scenario_comparison.json", report["scenarios"]),
        ("gate_evaluation.json", {"gate_1": report["gate_1"], "gate_2": report["gate_2"]}),
    ):
        (run_dir / name).write_text(json.dumps(content, indent=2, ensure_ascii=False), encoding="utf-8")
    return run_dir
