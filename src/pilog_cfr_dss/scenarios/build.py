from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from pilog_cfr_dss.calculations.capacity import gross_dwt_screen
from pilog_cfr_dss.models.contracts import CaseSnapshot, ScenarioEvidence


def _policy_decimal(value: Any, field: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise ValueError(f"INVALID_CLASS_POLICY:{field}") from error
    if not result.is_finite():
        raise ValueError(f"INVALID_CLASS_POLICY:{field}")
    return result


def build_scenarios(
    case: CaseSnapshot, fob_price_usd_mt: Decimal | None, class_policy: dict[str, Any]
) -> tuple[tuple[ScenarioEvidence, ...], dict[str, Any]]:
    """Two sale alternatives; vessel classes are evidence within CFR only."""
    if class_policy.get("screen_type") != "gross_dwt_only" or class_policy.get("unit") != "MT":
        raise ValueError("INVALID_CLASS_POLICY:screen_type_or_unit")
    classes = class_policy.get("classes", {})
    if set(classes) != {"Handysize", "Supramax"}:
        raise ValueError("INVALID_CLASS_POLICY:classes")
    cargo = case.number("dwcc_cargo_quantity_mt")
    case_dwt = case.number("dwt_mt")
    vessel_screen: dict[str, Any] = {}
    passed: list[str] = []
    for name in ("Handysize", "Supramax"):
        bounds = classes[name]
        minimum = _policy_decimal(bounds.get("min_dwt_mt"), f"{name}.min_dwt_mt")
        maximum = _policy_decimal(bounds.get("max_dwt_mt"), f"{name}.max_dwt_mt")
        feasible, reason = gross_dwt_screen(case_dwt, cargo, minimum, maximum)
        vessel_screen[name] = {
            "screen_pass": feasible, "reason": reason,
            "class_min_dwt_mt": str(minimum), "class_max_dwt_mt": str(maximum),
            "case_vessel_dwt_mt": str(case_dwt), "cargo_mt": str(cargo),
            "proof_level": "preliminary_gross_dwt_only",
        }
        if feasible:
            passed.append(name)
    if len(passed) > 1:
        raise ValueError("AMBIGUOUS_VESSEL_CLASS_POLICY")
    selected_class = passed[0] if passed else None
    fob = ScenarioEvidence(
        "FOB-BASELINE", "FOB", None, None, True, None, None,
        "PRICE_BASELINE_ONLY" if fob_price_usd_mt is not None else "HOLD_DATA_ISSUE",
        ("FOB_PRICE_AVAILABLE_NOT_PROFIT",) if fob_price_usd_mt is not None else ("MISSING_INDEX_OR_ALPHA",),
    )
    cfr = ScenarioEvidence(
        "CFR-PILOG", "CFR", selected_class, "PILOG",
        bool(selected_class), None, None,
        "NOT_CALCULATED" if selected_class else "INFEASIBLE",
        ("CLASS_SELECTED_BY_GROSS_DWT:" + selected_class, "ACTUAL_CARGO_CAPACITY_NOT_PROVEN")
        if selected_class else ("NO_VESSEL_CLASS_PASSED_DWT_SCREEN",),
    )
    return (fob, cfr), vessel_screen
