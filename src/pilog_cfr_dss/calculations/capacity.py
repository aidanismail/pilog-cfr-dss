from __future__ import annotations

from decimal import Decimal


def deadweight_headroom_mt(dwt_mt: Decimal, bunkers_mt: Decimal, constants_mt: Decimal, cargo_mt: Decimal) -> Decimal:
    if min(dwt_mt, bunkers_mt, constants_mt, cargo_mt) < 0:
        raise ValueError("INVALID_CAPACITY_INPUT")
    return dwt_mt - bunkers_mt - constants_mt - cargo_mt


def gross_dwt_screen(dwt_mt: Decimal, cargo_mt: Decimal, min_dwt_mt: Decimal, max_dwt_mt: Decimal) -> tuple[bool, str]:
    """Preliminary class/cargo screen; not a safe-loading or availability certificate."""
    if min(dwt_mt, cargo_mt, min_dwt_mt, max_dwt_mt) < 0 or min_dwt_mt > max_dwt_mt:
        raise ValueError("INVALID_DWT_SCREEN_INPUT")
    if cargo_mt > max_dwt_mt:
        return False, "CARGO_EXCEEDS_CLASS_MAX_DWT"
    if not min_dwt_mt <= dwt_mt <= max_dwt_mt:
        return False, "CASE_VESSEL_OUTSIDE_CLASS_RANGE"
    if cargo_mt > dwt_mt:
        return False, "CARGO_EXCEEDS_CASE_GROSS_DWT"
    return True, "PRELIMINARY_DWT_SCREEN_PASS"
