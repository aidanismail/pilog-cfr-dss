"""Explicit active-case policy; historical cases retain their original basis."""
import hashlib
from decimal import Decimal

from pilog_cfr_dss.sources.od_distance import payload_bytes, resolve_distance

BASIS_VERSION = "I4-INPUT.2"
COMMISSION_KEYS = ("freight_commission_fraction", "broker_fraction", "additional_commission_fraction")


def validate_case_basis(context: dict, rows: list[dict], values: dict) -> None:
    if context.get("case_basis_version") != BASIS_VERSION:
        return
    if any(values[key] != Decimal(0) for key in COMMISSION_KEYS):
        raise ValueError("ACTIVE_CASE_COMMISSION_MUST_BE_ZERO")
    if "od_reference" in context or context.get("od_usage") != "distance_only":
        raise ValueError("ACTIVE_OD_DISTANCE_ONLY")
    source = context["distance_reference"]
    if source.get("unit") != "NM" or source.get("source_status") != "observed_workbook_distance":
        raise ValueError("INVALID_OD_DISTANCE_RECORD")
    raw = source["raw_payload"]
    if hashlib.sha256(payload_bytes(raw)).hexdigest() != source["payload_sha256"]:
        raise ValueError("OD_DISTANCE_PAYLOAD_HASH_MISMATCH")
    resolved = resolve_distance(raw, values["loading_port"], values["discharging_port"], values["cargo_description"])
    if any(source[key] != value for key, value in resolved.items()):
        raise ValueError("OD_DISTANCE_SOURCE_BINDING_MISMATCH")
    if any(source[key] != values[key] for key in ("loading_port", "discharging_port", "cargo_description")):
        raise ValueError("OD_DISTANCE_ROUTE_MISMATCH")
    row = next(row for row in rows if row["key"] == "distance_nm")
    if values["distance_nm"] != Decimal(source["value"]) or row.get("source_reference") != source["source_reference"]:
        raise ValueError("OD_DISTANCE_SOURCE_BINDING_MISMATCH")


def distance_inputs(context: dict) -> dict[str, bytes]:
    if context.get("case_basis_version") != BASIS_VERSION:
        return {}
    return {"od_distance.json": payload_bytes(context["distance_reference"]["raw_payload"])}
