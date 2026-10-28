"""Fixed round windows, separate from financial formulas."""
from datetime import timedelta


def round_window(clock: dict, round_number: int):
    from pilog_cfr_dss.validation.iteration_04 import timestamp
    if clock.get("mode") != "fixed_window" or clock.get("round_duration_seconds") != 180:
        raise ValueError("INVALID_AUCTION_CLOCK")
    if type(round_number) is not int or round_number < 1:
        raise ValueError("INVALID_ROUND_NUMBER")
    start = timestamp(clock.get("starts_at")) + timedelta(seconds=180 * (round_number - 1))
    return start, start + timedelta(seconds=180)


def bid_in_round(bid: dict, clock: dict) -> bool:
    from pilog_cfr_dss.validation.iteration_04 import timestamp
    start, close = round_window(clock, bid["round"])
    return start <= timestamp(bid.get("submitted_at")) < close


def round_schedule(clock: dict, rounds: int) -> list[dict]:
    return [{"round": rd, "opens_at": round_window(clock, rd)[0].isoformat(),
             "closes_at": round_window(clock, rd)[1].isoformat()} for rd in range(1, rounds + 1)]
