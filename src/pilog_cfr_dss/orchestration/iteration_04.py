"""Local I4 orchestration, immutable input bytes, no production calls."""
import csv
import hashlib
import io
import json
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any
from uuid import uuid4

from pilog_cfr_dss.calculations.voyage_04 import voyage
from pilog_cfr_dss.calculations.pricing_04 import required_freight, economics, total_commission, contribution_delta, decision_metrics, commercial_financials
from pilog_cfr_dss.calculations.tender_04 import index_prices, bid_prices, od_delta, minimum_alpha
from pilog_cfr_dss.decisions.iteration_04 import evaluate_tender, decide, risk_label, review_step
from pilog_cfr_dss.models.iteration_04 import VERSION, REPORT_VERSION, METRICS_VERSION, MARKET_REPORT_VERSION, CLEAN_REPORT_VERSION, COMMERCIAL_REPORT_VERSION
from pilog_cfr_dss.validation.iteration_04 import load_case, number
from pilog_cfr_dss.reporting.iteration_04 import commercial_brief, calculation_audit
from pilog_cfr_dss.orchestration.price_records import utc_now, price_records
from pilog_cfr_dss.validation.market_sources import supporting_inputs
from pilog_cfr_dss.validation.case_basis import BASIS_VERSION, distance_inputs
from pilog_cfr_dss.validation.cost_forecast import effective_case, REVIEW_VERSION
from pilog_cfr_dss.calculations.commercial_review import commercial_review


def serial(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {k: serial(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [serial(v) for v in value]
    return value


def voyage_basis(case) -> dict[str, Any]:
    """One shared calculation path for the CLI and pre-tender UI service."""
    with localcontext() as precision:
        precision.prec = 40
        current_case = effective_case(case)
        costs = voyage(current_case)
        commission = total_commission(case.number(k) for k in (
            "freight_commission_fraction", "broker_fraction", "additional_commission_fraction"))
        target = number(case.context["pricing"]["target_tce"]["value"], "target TCE")
        computed = required_freight(costs["voyage_expenses_usd"], costs["total_days"],
                                    case.number("cargo_mt"), target, commission)
        rate = number(case.context["freight_tender"]["value"], "freight tender") if case.context.get("freight_tender") is not None else computed
        baseline = economics(costs, rate, case.number("cargo_mt"), commission)
        metrics = decision_metrics(baseline, case.number("cargo_mt"), commission,
                                   current_case.number("running_usd_day"), current_case.number("port_do_mt_day"),
                                   current_case.number("do_price_usd_mt"))
        quoted = economics(voyage(case), rate, case.number("cargo_mt"), commission)
        return {"baseline": baseline, "metrics": metrics, "commission": commission,
                "computed_rate": computed, "rate": rate, "effective_case": current_case,
                "quoted_baseline": quoted}


def commercial_details(case, basis: dict) -> dict:
    c = case.context
    review = commercial_review(basis["baseline"], basis["quoted_baseline"], case.number("cargo_mt"),
        basis["commission"], number(c["pricing"]["target_tce"]["value"], "target"), basis["metrics"]["freight_break_even_usd_mt"])
    profile = c.get("vessel_profile", {})
    benchmark = c.get("market_snapshot", {}).get("tc_rates", {}).get(profile.get("market_family"))
    quote = c.get("freight_tender") or {}
    review["pricing_bridge"] = {"benchmark": benchmark, "target": c["pricing"]["target_tce"],
        "indication_at_fix_usd_mt": quote.get("indicated_freight_usd_mt"),
        "current_indication_usd_mt": basis["computed_rate"], "fixed_offer_usd_mt": quote.get("value"),
        "quote_source_status": quote.get("source_status"), "price_id": quote.get("price_id"),
        "fixed_at": quote.get("fixed_at"), "cost_forecast": c.get("cost_forecast")}
    return review


def prepare_voyage(path: Path) -> dict[str, Any]:
    """Calculate a pre-tender estimate without inventing a bid or decision."""
    raw = path.read_bytes()
    case, dataset = load_case(path, pre_tender=True)
    content = dataset.read_bytes()
    if path.read_bytes() != raw or list(csv.DictReader(io.StringIO(content.decode("utf-8-sig")))) != list(case.rows):
        raise ValueError("INPUT_CHANGED_DURING_PREPARATION")
    basis = voyage_basis(case)
    c = case.context
    od = c.get("od_reference")
    captured = {"case_fixture.json": raw, dataset.name: content, **distance_inputs(c)}
    result = serial({"case_id": c["case_id"], "version": VERSION, "mode": "simulation",
        "advisory_only": True, "case": basis["effective_case"].values,
        "baseline": basis["baseline"], "metrics": basis["metrics"],
        "pricing": {"computed_freight_usd_mt": basis["computed_rate"],
                    "freight_tender_usd_mt": basis["rate"],
                    "rate_mode": "fixed_simulation" if c.get("freight_tender") is not None else "model_indication",
                    "source_record": c.get("freight_tender") or c["pricing"]["target_tce"],
                    "basis": c["pricing"], "commission_fraction": basis["commission"]},
        "od_comparison": {"rate_usd_mt": od["value"] if c.get("od_reference_valid") else None,
                          "is_gate": False, "is_savings_or_margin": False},
        "notes": case.notes})
    if c.get("od_usage") == "distance_only":
        result.pop("od_comparison")
        result["route_distance"] = c["distance_reference"]
    if c.get("commercial_review_version") == REVIEW_VERSION:
        result["commercial_review_version"] = REVIEW_VERSION
        with localcontext() as precision:
            precision.prec = 40
            result["commercial_review"] = serial(commercial_details(case, basis))
    result["input_hashes"] = {name: hashlib.sha256(data).hexdigest() for name, data in captured.items()}
    result["calculated_at"] = utc_now()
    result["pricing"]["calculated_at"] = result["calculated_at"]
    result["pricing"]["fixed_at"] = (c.get("freight_tender") or {}).get("fixed_at")
    return result


def evaluate(path: Path) -> dict[str, Any]:
    path = Path(path)
    report = {"case_id": path.stem, "version": VERSION, "report_version": REPORT_VERSION,
              "metrics_version": METRICS_VERSION, "mode": "simulation", "advisory_only": True,
              "audience": "INTERNAL_PI_PILOG", "classification": "INTERNAL_NOT_FOR_BUYERS"}
    captured = {}
    try:
        raw = path.read_bytes()
        captured["case_fixture.json"] = raw
        preview = json.loads(raw)
        if isinstance(preview, dict):
            name = preview.get("voyage_dataset")
            if isinstance(name, str) and Path(name).name == name and name.endswith(".csv"):
                captured[name] = (path.parent / name).read_bytes()
        case, dataset = load_case(path)
        dataset_bytes = dataset.read_bytes()
        # Ensure calculations and snapshots refer to the exact same reads.
        if path.read_bytes() != raw:
            raise ValueError("CASE_CHANGED_DURING_LOAD")
        parsed_rows = list(csv.DictReader(io.StringIO(dataset_bytes.decode("utf-8-sig"))))
        if parsed_rows != list(case.rows) or captured.get(dataset.name) != dataset_bytes:
            raise ValueError("DATASET_CHANGED_DURING_LOAD")
        captured[dataset.name] = dataset_bytes
        c = case.context
        captured.update(supporting_inputs(c))
        captured.update(distance_inputs(c))
        with localcontext() as precision:
            precision.prec = 40
            basis = voyage_basis(case)
            commission, computed_rate, rate = basis["commission"], basis["computed_rate"], basis["rate"]
            baseline, metrics = basis["baseline"], basis["metrics"]
            index = index_prices(c["market_index"])
            floor = number(c["oe_hps"]["value"], "OE/HPS")
            metrics["minimum_alpha_usd_mt"] = minimum_alpha(index["index_usd_mt"], floor)
            tender = evaluate_tender(bid_prices(index["index_usd_mt"], floor, rate, c["bids"]), c)
            financials = commercial_financials(case.number("cargo_mt"), tender["bids"], baseline)
            scenarios = [{"scenario_id": "baseline", "label": "Baseline", "economics": baseline}]
            for shock in c["scenarios"]:
                changed = voyage(basis["effective_case"], number(shock["fuel_price_increase_fraction"], "fuel shock"), number(shock["extra_port_days"], "delay"))
                scenarios.append({"scenario_id": shock["scenario_id"], "label": shock.get("label", shock["scenario_id"]),
                                  "economics": economics(changed, rate, case.number("cargo_mt"), commission)})
            for scenario in scenarios:
                contribution = scenario["economics"]["contribution_usd"]
                scenario["interpretation"] = risk_label(contribution)
                scenario["change_from_baseline_usd"] = contribution_delta(contribution, baseline["contribution_usd"])
            od = c.get("od_reference")
            od_rate = number(od["value"], "OD") if c.get("od_reference_valid") else None
            comparison = {"rate_usd_mt": od_rate, "system_rate_usd_mt": rate,
                          "arithmetic_difference_usd_mt": od_delta(rate, od_rate) if od_rate is not None else None,
                          "quote_basis": "one_way_shipment", "od_cost_coverage": "includes_return",
                          "system_cost_coverage": "laden_only", "is_gate": False, "is_savings_or_margin": False,
                          "source": od}
            report.update({"case_id": c["case_id"], "case": basis["effective_case"].values, "index": index, "oe_hps_usd_mt": floor,
                           "pricing": {"computed_freight_usd_mt": computed_rate, "freight_tender_usd_mt": rate,
                                       "rate_mode": "fixed_simulation" if c.get("freight_tender") is not None else "model_indication",
                                       "source_record": c.get("freight_tender") or c["pricing"]["target_tce"],
                                       "commercial_approval": "NOT_EVIDENCED_BY_SIMULATION",
                                       "basis": c["pricing"], "commission_fraction": commission,
                                       "rounding": "ROUND_CEILING to 0.0001 USD/MT"},
                           "baseline": baseline, "metrics": metrics, "tender": tender, "scenarios": scenarios,
                           "commercial_financials": financials,
                           "od_comparison": comparison, "recommendation": decide(case, tender, baseline, scenarios),
                           "notes": case.notes, "input_lineage": {"voyage_fields": case.rows, "context": c}})
            if c.get("case_basis_version") == BASIS_VERSION:
                report.pop("od_comparison")
                report["route_distance"] = c["distance_reference"]
                report["report_version"] = CLEAN_REPORT_VERSION
            report["_calculated_at"] = utc_now()
            if c.get("market_snapshot"):
                report["report_version"] = CLEAN_REPORT_VERSION if c.get("case_basis_version") == BASIS_VERSION else MARKET_REPORT_VERSION
                report["rule_extension"] = "TENDER-CLOCK.1" if c.get("auction_clock") else None
                calculated_at = report["_calculated_at"]
                report["pricing"].update(calculated_at=calculated_at, fixed_at=(c.get("freight_tender") or {}).get("fixed_at"))
                report["price_records"] = price_records(report, c, calculated_at)
            if c.get("commercial_review_version") == REVIEW_VERSION:
                report["report_version"] = COMMERCIAL_REPORT_VERSION
                report["commercial_review"] = commercial_details(case, basis)
    except (ValueError, TypeError, KeyError, OSError, ArithmeticError, AttributeError) as error:
        report["recommendation"] = {"action": "NO_GO", "summary": "Belum aman merekomendasikan CFR karena input tidak dapat dihitung: " + str(error),
                                    "reason_codes": ["DATA_ISSUE", str(error)], "gate_a": "NOT_EVALUATED", "gate_b": "NOT_EVALUATED",
                                    "human_approval": "PENDING_HUMAN_REVIEW",
                                    "next_steps": [review_step("CORRECT_CRITICAL_INPUT", "Pemilik input kasus",
                                                              "Perbaiki field/unit/struktur yang dilaporkan: " + str(error) + ". Jalankan ulang; jangan mengisi default nol.")],
                                    "checks": [{"name": "Input hitungan penting", "status": "Tidak lolos", "evidence": str(error)}]}
    report = serial(report)
    report["input_hashes"] = {name: hashlib.sha256(content).hexdigest() for name, content in captured.items()}
    report["_captured_inputs"] = captured
    return report


def fixed_freight_record(report: dict[str, Any]) -> dict[str, Any]:
    """Record a calculated indication as an explicit SIMULATION price, not approval.

    Called only by an intentional preparation step, never by bid evaluation.
    Existing fixed rates must not be overwritten as a side effect of rerunning.
    """
    if "baseline" not in report:
        raise ValueError("CANNOT_PREPARE_FREIGHT_FROM_INVALID_INPUT")
    pricing = report["pricing"]
    if pricing["rate_mode"] == "fixed_simulation":
        return pricing["source_record"]
    record = {"value": pricing["computed_freight_usd_mt"], "unit": "USD/MT",
            "price_id": "freight_" + uuid4().hex, "calculated_at": report.get("calculated_at") or report.get("_calculated_at"),
            "fixed_at": utc_now(), "actor_id": None, "actor_type": "local_session", "actor_role": None,
            "source_status": "simulation_only_derived_fixed_tender_rate",
            "source_reference": "I4 deterministic pricing indication; intentionally fixed during input preparation",
            "formula_version": report["version"],
            "pricing_basis": pricing["basis"],
            "voyage_dataset_sha256": {k: v for k, v in report["input_hashes"].items() if k.endswith(".csv")},
            "note": "Fixed for simulation evaluation only; no commercial approval or buyer acceptance inferred."}
    if report.get("commercial_review_version") == REVIEW_VERSION:
        record["indicated_freight_usd_mt"] = pricing["computed_freight_usd_mt"]
        record["buyer_acceptance"] = "NOT_RECORDED"
    return record


def persist_run(report: dict[str, Any], output_root: Path) -> Path:
    created = datetime.now(timezone.utc)
    run_id = "i4_" + created.strftime("%Y%m%dT%H%M%S%fZ") + "_" + uuid4().hex[:8]
    output = Path(output_root) / run_id
    snapshot = output / "input_snapshot"
    snapshot.mkdir(parents=True, exist_ok=False)
    public = {k: v for k, v in report.items() if not k.startswith("_")}
    # One immutable identity shared by JSON, brief and audit; no invented legacy date.
    public.update({"run_id": run_id, "generated_at": created.isoformat()})
    for name, content in report.get("_captured_inputs", {}).items():
        if Path(name).name != name or hashlib.sha256(content).hexdigest() != public["input_hashes"][name]:
            raise ValueError("INVALID_SNAPSHOT")
        (snapshot / name).write_bytes(content)
    (output / "result.json").write_text(json.dumps(public, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "commercial_decision_brief.md").write_text(commercial_brief(public), encoding="utf-8")
    (output / "calculation_audit.md").write_text(calculation_audit(public), encoding="utf-8")
    return output
