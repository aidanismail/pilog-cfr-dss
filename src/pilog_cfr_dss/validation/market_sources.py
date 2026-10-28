"""Offline binding of market observations to their captured source payloads."""
import hashlib
from pilog_cfr_dss.sources.fearnpulse import normalize_payloads


def validate_market_binding(context: dict, rows: list[dict], values: dict) -> None:
    snapshot = context.get("market_snapshot")
    if snapshot is None:
        return
    normalized = normalize_payloads(snapshot["raw_payloads"], snapshot["fetched_at"])
    for key in ("tc_rates", "bunkers", "report_id", "report_published_at", "payload_hashes"):
        if normalized[key] != snapshot[key]:
            raise ValueError("MARKET_SNAPSHOT_MISMATCH:" + key)
    profile = context["vessel_profile"]
    family = profile["market_family"]
    target = context["pricing"]["target_tce"]
    if target.get("source_status") != "simulation_only_user_input":
        if str(target["value"]) != snapshot["tc_rates"][family]["value"] or target.get("source_snapshot_id") != snapshot["snapshot_id"]:
            raise ValueError("TARGET_TCE_SOURCE_BINDING_MISMATCH")
    by_key = {row["key"]: row for row in rows}
    for key, quote in snapshot["bunkers"].items():
        if by_key[key].get("source_status") != "simulation_only_user_input" and str(values[key]) != quote["value"]:
            raise ValueError("BUNKER_SOURCE_BINDING_MISMATCH:" + key)
    for key, expected in profile["fields"].items():
        if by_key[key].get("source_status") != "simulation_only_user_input" and str(values[key]) != expected:
            raise ValueError("PROFILE_SOURCE_BINDING_MISMATCH:" + key)
    if values["vessel_class"] != profile["vessel_class"]:
        raise ValueError("PROFILE_CLASS_MISMATCH")
    if any("baltic" in str(row.get("source_reference", "")).lower() for row in rows):
        raise ValueError("LEGACY_BALTIC_INPUT_IN_ACTIVE_MARKET_CASE")


def supporting_inputs(context: dict) -> dict[str, bytes]:
    snapshot = context.get("market_snapshot")
    if not snapshot:
        return {}
    captured = {}
    for name, content in snapshot["raw_payloads"].items():
        data = content.encode("utf-8")
        if hashlib.sha256(data).hexdigest() != snapshot["payload_hashes"][name]:
            raise ValueError("MARKET_PAYLOAD_HASH_MISMATCH")
        captured[name] = data
    return captured
