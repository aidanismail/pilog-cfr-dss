from __future__ import annotations

from typing import Any, Iterable

from pilog_cfr_dss.models.contracts import QualityResult, ScenarioEvidence


def gate_1(quality: QualityResult, case_context: dict[str, Any]) -> dict[str, Any]:
    """Can a pre-offer case enter CFR analysis? Economics belongs to Gate 2."""
    if quality.status == "BLOCK":
        return {"outcome": "HOLD_DATA_ISSUE", "reasons": ["CRITICAL_QUALITY_BLOCK"]}
    if case_context.get("mode") != "simulation" or case_context.get("decision_stage") != "pre_offer":
        return {"outcome": "HOLD_DATA_ISSUE", "reasons": ["INVALID_SIMULATION_STAGE"]}
    buyer = case_context.get("buyer_response")
    if buyer == "declined_cfr":
        return {"outcome": "CFR_OUT_OF_SCOPE", "reasons": ["BUYER_DECLINED_CFR"]}
    if buyer != "not_approached":
        return {"outcome": "HOLD_DATA_ISSUE", "reasons": ["UNKNOWN_BUYER_RESPONSE"]}
    if not case_context.get("commodity_seller") or case_context.get("freight_provider") != "PILOG":
        return {"outcome": "HOLD_DATA_ISSUE", "reasons": ["MISSING_CONTRACTING_ROLES"]}
    evidence = case_context.get("commercial_evidence", {})
    explicit_no = [
        name for name in ("seller_authorized", "contract_allows_ocean_freight", "pilog_has_freight_scope")
        if evidence.get(name) is False
    ]
    if explicit_no:
        return {
            "outcome": "CFR_OUT_OF_SCOPE",
            "reasons": [f"CFR_SCOPE_REJECTED:{name}" for name in explicit_no],
        }
    return {
        "outcome": "CFR_ELIGIBLE",
        "reasons": ["PRE_OFFER_CASE_READY", "BUYER_NOT_APPROACHED_IS_NORMAL"],
    }


def gate_2(
    gate1: dict[str, Any],
    scenarios: Iterable[ScenarioEvidence],
    objective: str | None,
    simulation_assumptions: Iterable[str] = (),
) -> dict[str, Any]:
    """Return an advisory action, never a quote or commercial approval."""
    scenarios = tuple(scenarios)
    fob = next((item for item in scenarios if item.sales_term == "FOB"), None)
    cfr = next((item for item in scenarios if item.sales_term == "CFR"), None)
    results = []
    if fob is not None:
        results.append({
            "scenario_id": fob.scenario_id,
            "outcome": fob.calculation_status,
            "reasons": [*fob.reasons, "FOB_COMMODITY_PROFIT_NOT_ASSESSED"],
        })
    if gate1["outcome"] == "HOLD_DATA_ISSUE":
        return {
            "outcome": "NOT_STARTED", "reason": "GATE_1_DATA_HOLD",
            "scenario_results": results, "selected_scenario_id": None,
            "reason_codes": list(gate1["reasons"]),
            "next_action": "Perbaiki input teknis, lalu hitung ulang.",
        }
    if gate1["outcome"] == "CFR_OUT_OF_SCOPE":
        return {
            "outcome": "DEFER_FOB_REVIEW", "scenario_results": results,
            "selected_scenario_id": None,
            "reason_codes": [*gate1["reasons"], "FOB_ECONOMICS_NOT_AVAILABLE"],
            "next_action": "Minta PI seller/Commercial menilai opsi FOB; jangan mengasumsikan profit FOB.",
        }
    if cfr is None:
        return {
            "outcome": "HOLD_DATA_OR_DEFINITION", "scenario_results": results,
            "selected_scenario_id": None, "reason_codes": ["MISSING_CFR_ALTERNATIVE"],
            "next_action": "Lengkapi alternatif CFR.",
        }
    reasons = list(cfr.reasons)
    if cfr.feasible is False:
        cfr_outcome = "INFEASIBLE_DWT_SCREEN"
    elif cfr.feasible is not True or cfr.comparable is not True or cfr.contribution_usd is None:
        cfr_outcome = "HOLD_DATA_OR_DEFINITION"
    elif objective != "net_freight_contribution_usd":
        cfr_outcome = "HOLD_DATA_OR_DEFINITION"
        reasons.append("UNCONFIRMED_DECISION_OBJECTIVE")
    elif cfr.contribution_usd <= 0:
        cfr_outcome = "NONPOSITIVE_FREIGHT_CONTRIBUTION"
        reasons.append("CONTRIBUTION_NOT_POSITIVE")
    else:
        cfr_outcome = "POSITIVE_FREIGHT_CONTRIBUTION_FOR_REVIEW"
    results.append({"scenario_id": cfr.scenario_id, "outcome": cfr_outcome, "reasons": reasons})
    if cfr_outcome == "POSITIVE_FREIGHT_CONTRIBUTION_FOR_REVIEW":
        return {
            "outcome": "CFR_CANDIDATE_PENDING_HUMAN_REVIEW",
            "scenario_results": results, "selected_scenario_id": cfr.scenario_id,
            "reason_codes": [
                "PRELIMINARY_DWT_SCREEN_PASS", "POSITIVE_PILOG_FREIGHT_CONTRIBUTION",
                "SIMULATION_ASSUMPTIONS_PRESENT" if tuple(simulation_assumptions) else "HUMAN_REVIEW_REQUIRED",
                "FOB_COMMODITY_PROFIT_NOT_ASSESSED",
            ],
            "next_action": "Validasi kapal, biaya, harga, dan kewenangan dengan atasan/PI seller; baru setelah disetujui dekati buyer.",
        }
    if cfr_outcome == "HOLD_DATA_OR_DEFINITION":
        return {
            "outcome": "HOLD_DATA_OR_DEFINITION", "scenario_results": results,
            "selected_scenario_id": None,
            "reason_codes": [*reasons, "CFR_ECONOMICS_NOT_COMPARABLE"],
            "next_action": "Lengkapi definisi/input yang ditandai; jangan keluarkan kandidat CFR.",
        }
    return {
        "outcome": "DEFER_FOB_REVIEW", "scenario_results": results,
        "selected_scenario_id": None,
        "reason_codes": [*reasons, "FOB_ECONOMICS_NOT_AVAILABLE"],
        "next_action": "Uji reprice/redesign CFR atau minta PI seller/Commercial menilai ekonomi FOB; NO_BID belum dapat dibuktikan.",
    }
