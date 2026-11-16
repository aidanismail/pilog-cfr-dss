from __future__ import annotations

from decimal import Decimal


def require_cargo_within_gross_dwt(cargo_mt: Decimal, dwt_mt: Decimal) -> None:
    """Reject impossible gross loads; passing does not establish DWCC."""
    if not cargo_mt.is_finite() or not dwt_mt.is_finite() or min(cargo_mt, dwt_mt) <= 0:
        raise ValueError('INVALID_CAPACITY_INPUT')
    if cargo_mt > dwt_mt:
        raise ValueError('CARGO_EXCEEDS_CASE_GROSS_DWT')


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


def bulk_capacity(profile: dict, cargo: Decimal, sf: Decimal, draft_limits: list) -> dict:
    """Weight/volume screen and labelled linear-TPC draft approximation."""
    from pilog_cfr_dss.validation.numbers import number
    dwt = number(profile["dwt_mt"], "dwt_mt")
    grain = number(profile["grain_m3"], "grain_m3")
    allowance = sum((number(profile[key], key, Decimal(0))
                     for key in ("bunkers_allowance_mt", "constants_allowance_mt")), Decimal(0))
    if min(dwt, grain, cargo, sf) <= 0 or allowance >= dwt:
        raise ValueError("INVALID_BULK_CAPACITY")
    volume_limit = grain / sf
    weight_limit = dwt - allowance
    limits = [number(x, "port_draft_m") for x in draft_limits if x is not None]
    reduction = Decimal(0)
    if limits:
        summer = number(profile["summer_draft_m"], "summer_draft_m")
        tpc = number(profile["tpc_mt_cm"], "tpc_mt_cm")
        if min(*limits, summer, tpc) <= 0:
            raise ValueError("INVALID_DRAFT_SCREEN")
        reduction = max(Decimal(0), summer - min(limits)) * 100 * tpc
    draft_limit = weight_limit - reduction
    capacity = min(volume_limit, draft_limit)
    checks = [
        {"code": "WEIGHT", "status": "PASS" if cargo <= weight_limit else "FAIL", "limit_mt": weight_limit},
        {"code": "VOLUME", "status": "PASS" if cargo <= volume_limit else "FAIL", "limit_mt": volume_limit},
        {"code": "DRAFT", "status": ("NOT_MODELLED" if not limits else
         "FAIL" if cargo > draft_limit else "PARTIAL_ESTIMATE" if len(limits) < 2 else "ESTIMATED_PASS"),
         "limit_mt": draft_limit if limits else None},
    ]
    return {"feasible": cargo <= capacity, "limit_mt": capacity,
            "binding": "VOLUME" if volume_limit <= draft_limit else "DRAFT" if reduction > 0 else "WEIGHT",
            "volume_required_m3": cargo * sf, "checks": checks,
            "draft_method": "linear_TPC_screen_not_loading_approval" if limits else "not_modelled"}
