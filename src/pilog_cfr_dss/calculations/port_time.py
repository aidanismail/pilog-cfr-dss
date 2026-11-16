"""Operational time estimation, not charter-party laytime settlement."""
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal, ROUND_CEILING
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from pilog_cfr_dss.models.freight_desk import TERMS
from pilog_cfr_dss.validation.numbers import number

DAY = Decimal(86400)


def seconds(delta):
    return Decimal(delta.days * 86400 + delta.seconds) + Decimal(delta.microseconds) / 1000000


def advance(start, days):
    micros = (days * DAY * 1000000).to_integral_value(rounding=ROUND_CEILING)
    return start + timedelta(microseconds=int(micros))


def working_windows(term, weekday):
    """Complement of the weekly exclusion; wrap-around Monday is explicit."""
    exclusion = TERMS[term]["excluded_interval"]
    if exclusion is None:
        return [(0, 1440)]
    a, b, c, d = exclusion
    first, last = a * 1440 + b, c * 1440 + d
    lo, hi = weekday * 1440, (weekday + 1) * 1440
    result = [(lo, hi)]
    for left, right in [(first, last), (first - 10080, last - 10080)]:
        pieces = []
        for x, y in result:
            if left > x:
                pieces.append((x, min(y, left)))
            if right < y:
                pieces.append((max(x, right), y))
        result = [(x, y) for x, y in pieces if y > x]
    return [(x - lo, y - lo) for x, y in result]


def port_duration(quantity, port, start):
    rate = number(port["rate_mt_day"], "rate_mt_day")
    if rate <= 0 or quantity <= 0:
        raise ValueError("INVALID_HANDLING_RATE_OR_QUANTITY")
    term = port["terms"]
    if term not in TERMS:
        raise ValueError("UNKNOWN_TERMS")
    work_days = quantity / rate
    mode = port.get("time_basis", "factor")
    if mode == "factor":
        days = work_days * Decimal(TERMS[term]["factor"])
        return days, advance(start, days)
    if mode != "calendar":
        raise ValueError("UNKNOWN_TIME_BASIS")
    calendar = port.get("calendar", {})
    if not isinstance(calendar, dict):
        raise ValueError("INVALID_CALENDAR")
    try:
        zone = ZoneInfo(calendar["timezone"])
    except (KeyError, ZoneInfoNotFoundError):
        raise ValueError("CALENDAR_TIMEZONE_REQUIRED") from None
    holidays = {datetime.fromisoformat(x).date() for x in calendar.get("holidays", [])}
    remaining = work_days * DAY
    cursor = start.astimezone(timezone.utc)
    local_date = cursor.astimezone(zone).date()
    custom = calendar.get("windows")
    if custom is not None and not isinstance(custom, dict):
        raise ValueError("INVALID_CALENDAR_WINDOWS")
    # Finite horizon prevents a malformed/no-work calendar looping forever.
    for offset in range(731):
        day = local_date + timedelta(days=offset)
        if day in holidays:
            continue
        windows = custom.get(str(day.weekday()), []) if custom is not None else working_windows(term, day.weekday())
        previous = 0
        for a, b in windows:
            if isinstance(a, bool) or isinstance(b, bool) or not (0 <= a < b <= 1440) or a < previous:
                raise ValueError("INVALID_CALENDAR_WINDOWS")
            previous = b
            midnight = datetime.combine(day, time(), zone)
            left = (midnight + timedelta(minutes=a)).astimezone(timezone.utc)
            right = (midnight + timedelta(minutes=b)).astimezone(timezone.utc)
            left = max(left, cursor)
            if right <= left:
                continue
            available = seconds(right - left)
            if remaining <= available:
                end = advance(left, remaining / DAY)
                return seconds(end - start.astimezone(timezone.utc)) / DAY, end
            remaining -= available
            cursor = right
    raise ValueError("CALENDAR_HORIZON_EXCEEDED")
