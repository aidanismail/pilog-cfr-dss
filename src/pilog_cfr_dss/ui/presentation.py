"""Presentation of active inputs and provenance; no business arithmetic."""
from copy import deepcopy


def active_inputs(case) -> dict:
    """Show effective values without replacing the immutable base/source rows."""
    values = case.current_values()
    forecast = case.context.get("cost_forecast", {})
    overrides = forecast.get("overrides", {})
    records = {}
    for original in case.rows:
        row = deepcopy(original)
        key = row["key"]
        row["value"] = values[key]
        if key in overrides:
            row.update(deepcopy(overrides[key]))
            row["note"] = forecast["reason"]
        records[key] = row
    return records


def source_label(record: dict, sheet: str = "") -> str:
    status = record.get("source_status", "")
    if "cost_reforecast" in status:
        return "Estimasi terbaru"
    if "user_input" in status:
        return "Input manual"
    if status == "observed_public_market":
        return "Fearnpulse"
    if status == "observed_workbook_profile_transfer":
        return "Voyage Estimate · " + sheet
    if status == "observed_workbook_distance":
        return "OD · jarak"
    if status == "inherited_simulation_proxy":
        return "Acuan historis"
    if status == "simulation_only_assumption":
        return "Asumsi kasus"
    if status == "approved_case_policy":
        return "Kebijakan kasus"
    return "Parameter kasus"
