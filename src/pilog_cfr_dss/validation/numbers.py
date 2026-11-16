"""Shared primitives independent of any historical tender schema."""
from datetime import datetime
from decimal import Decimal, InvalidOperation


def number(value, key="value", minimum=None):
    if value is None or isinstance(value, (bool, dict, list)) or not str(value).strip():
        raise ValueError("INVALID_NUMBER:" + key)
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError("INVALID_NUMBER:" + key) from None
    if not result.is_finite() or (minimum is not None and result < minimum):
        raise ValueError("INVALID_RANGE:" + key)
    return result


def timestamp(value):
    try:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("INVALID_TIMESTAMP") from None
    if result.tzinfo is None:
        raise ValueError("TIMESTAMP_REQUIRES_TIMEZONE")
    return result


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("DUPLICATE_JSON_KEY:" + key)
        result[key] = value
    return result
