"""Advisory-only, two-outcome I3 CFR gates. NO GO can mean data cannot support GO."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from pilog_cfr_dss.calculations.capacity import gross_dwt_screen
from pilog_cfr_dss.models.contracts import CaseSnapshot
from pilog_cfr_dss.validation.iteration_03 import decimal


def evaluate_cfr_gates(
    case: CaseSnapshot, fixture: dict[str, Any], bids: list[dict[str, Any]],
    economics: dict[str, Any], vessel_policy: dict[str, Any],
) -> dict[str, Any]:
    selected_id = fixture["pi_selected_bid"]["bid_id"]
    selected = next((bid for bid in bids if bid["bid_id"] == selected_id), None)
    eligible = [bid for bid in bids if bid["eligible_oe_floor"]]
    if not eligible:
        return {
            "action": "NO_GO", "reason_category": "TENDER_PRICE_FLOOR",
            "reason_codes": ["NO_ELIGIBLE_BID_FOB_BELOW_OE_HPS"],
            "gate_a": "FAIL", "gate_b": "NOT_EVALUATED", "selected_bid_id": None,
            "next_action": "PI Commercial melanjutkan/meninjau tender; jangan menerbitkan komitmen CFR PILOG.",
        }
    if selected is None:
        return {
            "action": "NO_GO", "reason_category": "DATA_OR_TENDER_SELECTION",
            "reason_codes": ["PI_SELECTED_BID_MISSING"],
            "gate_a": "FAIL", "gate_b": "NOT_EVALUATED", "selected_bid_id": None,
            "next_action": "PI Commercial harus menetapkan kandidat tender sebelum evaluasi CFR.",
        }
    if not selected["eligible_oe_floor"]:
        return {
            "action": "NO_GO", "reason_category": "TENDER_PRICE_FLOOR",
            "reason_codes": ["SELECTED_BID_FOB_BELOW_OE_HPS"],
            "gate_a": "FAIL", "gate_b": "NOT_EVALUATED", "selected_bid_id": selected_id,
            "next_action": "Kembalikan kandidat ke PI Commercial; harga FOB bid di bawah OE/HPS.",
        }
    if vessel_policy.get("screen_type") != "gross_dwt_only" or vessel_policy.get("unit") != "MT":
        raise ValueError("INVALID_VESSEL_POLICY")
    classes = vessel_policy.get("classes", {})
    if set(classes) != {"Handysize", "Supramax"}:
        raise ValueError("INVALID_VESSEL_CLASSES")
    vessel_results = {}
    passed = []
    for name in ("Handysize", "Supramax"):
        bounds = classes[name]
        feasible, reason = gross_dwt_screen(
            case.number("dwt_mt"), case.number("dwcc_cargo_quantity_mt"),
            decimal(bounds["min_dwt_mt"], f"{name}.min_dwt"),
            decimal(bounds["max_dwt_mt"], f"{name}.max_dwt"),
        )
        vessel_results[name] = {"screen_pass": feasible, "reason": reason, "proof_level": "preliminary_gross_dwt_only"}
        if feasible:
            passed.append(name)
    if len(passed) > 1:
        raise ValueError("AMBIGUOUS_VESSEL_CLASS")
    contribution = decimal(economics["pilog_freight_contribution_usd"], "pilog_contribution")
    headroom = decimal(economics["dwt_headroom_after_allowances_mt"], "dwt_headroom")
    reasons = []
    if not passed:
        reasons.append("NO_VESSEL_CLASS_PASSED_DWT_SCREEN")
    if headroom < 0:
        reasons.append("CARGO_EXCEEDS_DWT_AFTER_ALLOWANCES")
    if contribution < 0:
        reasons.append("NEGATIVE_PILOG_FREIGHT_CONTRIBUTION")
    if reasons:
        return {
            "action": "NO_GO", "reason_category": "CFR_EXECUTION_OR_ECONOMICS",
            "reason_codes": reasons, "gate_a": "PASS", "gate_b": "FAIL",
            "selected_bid_id": selected_id, "selected_vessel_class": passed[0] if passed else None,
            "vessel_screen": vessel_results,
            "next_action": "PILOG Chartering/BusDev meninjau kapal atau ekonomi freight; PI tidak melanjutkan CFR dari snapshot ini.",
        }
    return {
        "action": "GO", "reason_category": "CFR_REVIEW_CANDIDATE",
        "reason_codes": ["TENDER_OE_FLOOR_MET", "PRELIMINARY_VESSEL_SCREEN_PASSED", "PILOG_CONTRIBUTION_NONNEGATIVE"],
        "gate_a": "PASS", "gate_b": "PASS", "selected_bid_id": selected_id,
        "selected_vessel_class": passed[0], "vessel_screen": vessel_results,
        "next_action": "Ajukan hasil CFR dan asumsi simulasi kepada pejabat PI/PILOG untuk review; jangan otomatis award atau fixture kapal.",
    }
