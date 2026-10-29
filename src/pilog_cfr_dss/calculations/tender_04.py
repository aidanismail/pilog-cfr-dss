"""Index, bid-price arithmetic and reference delta; no award or I/O."""
from decimal import Decimal
from typing import Any
from pilog_cfr_dss.calculations.tender import midpoint, average_two_publishers


def index_prices(observations: dict[str, Any]) -> dict[str, Decimal]:
    mids = {key: midpoint(Decimal(str(observations[key]["low"])), Decimal(str(observations[key]["high"])))
            for key in ("argus", "fertecon")}
    return {**mids, "index_usd_mt": average_two_publishers(mids["argus"], mids["fertecon"])}


def bid_prices(index: Decimal, floor: Decimal, freight: Decimal, bids: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for bid in bids:
        alpha = Decimal(str(bid["alpha_usd_mt"]))
        fob = index + alpha
        if fob < 0:
            raise ValueError("NEGATIVE_FOB")
        gap = fob - floor
        result.append({**bid, "fob_usd_mt": fob, "freight_usd_mt": freight, "cfr_usd_mt": fob + freight,
                       "oe_gap_usd_mt": gap, "floor_shortfall_usd_mt": max(-gap, Decimal(0))})
    return result


def minimum_alpha(index: Decimal, floor: Decimal) -> Decimal:
    """Internal floor arithmetic, not a mandatory bid or commodity profit."""
    if any(not isinstance(x, Decimal) or not x.is_finite() or x < 0 for x in (index, floor)):
        raise ValueError("INVALID_FLOOR_METRIC_INPUT")
    return floor - index


def od_delta(freight: Decimal, od: Decimal) -> Decimal:
    return freight - od
