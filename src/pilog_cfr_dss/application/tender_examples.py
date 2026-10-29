"""Seeded synthetic editor inputs. Never used by calculations or gate rules."""
from copy import deepcopy
from datetime import timedelta
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP, localcontext
import hashlib
import json
import random
import secrets

from pilog_cfr_dss.models.tender_clock import round_window
from pilog_cfr_dss.orchestration.price_records import utc_now

VERSION = "TENDER-EXAMPLE.1"
BID_KEYS = ("bid_id", "buyer_id", "round", "sequence", "alpha_usd_mt", "status", "submitted_at", "valid_until")
RISK_KEYS = ("scenario_id", "label", "fuel_price_increase_fraction", "extra_port_days")


def input_digest(bids: list[dict], scenarios: list[dict]) -> str:
    def clean(rows, keys):
        return [{key: str(row[key]).strip() for key in keys
                 if row.get(key) is not None and str(row[key]).strip()} for row in rows]
    content = {"bids": clean(bids, BID_KEYS), "scenarios": clean(scenarios, RISK_KEYS)}
    return hashlib.sha256(json.dumps(content, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def generate_example(case, seed: int | None = None) -> dict:
    if not case.fixed:
        raise ValueError("FREIGHT_NOT_FIXED")
    seed = secrets.randbits(64) if seed is None else seed
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed < 2**64:
        raise ValueError("INVALID_EXAMPLE_SEED")
    rng = random.Random(seed)
    prices = case.market_summary()
    clock = case.context.get("auction_clock")
    with localcontext() as precision:
        precision.prec = 40
        index = Decimal(prices["index_usd_mt"])
        center = Decimal(prices["minimum_alpha_usd_mt"])
        lower = (-index).quantize(Decimal("0.01"), rounding=ROUND_CEILING)
        # A shared market mood plus buyer variation; no desired-outcome branch.
        mood = rng.randint(-1800, 1400)
        paths = []
        for _ in range(3):
            offset = mood + rng.randint(-300, 300) - rng.randint(150, 500)
            offers = []
            for _ in range(3):
                offset += rng.randint(25, 200)
                offers.append(str(max(lower, (center + Decimal(offset) / 100).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP))))
            paths.append(offers)
        bids = []
        for round_number in range(1, 4):
            for buyer in range(1, 4):
                bid = {"bid_id": f"R{round_number}-B{buyer}", "buyer_id": f"BUYER-{buyer}",
                       "round": round_number, "sequence": buyer,
                       "alpha_usd_mt": paths[buyer-1][round_number-1], "status": "active"}
                if clock:
                    opened, _ = round_window(clock, round_number)
                    bid["submitted_at"] = (opened + timedelta(seconds=rng.randint(15, 165))).isoformat()
                bids.append(bid)
        percentage = rng.randint(5, 45)
        fraction = str(Decimal(percentage) / 100)
        days = str(rng.choice((2, 3, 5, 7, 10, 14, 21, 30)))
    fuel_label, delay_label = f"BBM naik {percentage}%", f"Delay pelabuhan {days} hari"
    risks = [
        {"scenario_id": "fuel_up", "label": fuel_label, "fuel_price_increase_fraction": fraction, "extra_port_days": "0"},
        {"scenario_id": "port_delay", "label": delay_label, "fuel_price_increase_fraction": "0", "extra_port_days": days},
        {"scenario_id": "fuel_and_delay", "label": fuel_label + " + " + delay_label,
         "fuel_price_increase_fraction": fraction, "extra_port_days": days},
    ]
    return {"bids": bids, "scenarios": risks,
            "evaluation_cutoff": round_window(clock, 3)[1].isoformat() if clock else case.context["evaluation_cutoff"],
            "metadata": {"version": VERSION, "seed": str(seed), "generated_at": utc_now(),
                         "source_status": "simulation_only_randomized_example",
                         "basis_price_id": case.context["freight_tender"].get("price_id"),
                         "basis_index_usd_mt": prices["index_usd_mt"],
                         "basis_oe_hps_usd_mt": case.context["oe_hps"]["value"],
                         "basis_auction_clock": deepcopy(clock),
                         "generated_evaluation_cutoff": round_window(clock, 3)[1].isoformat() if clock else case.context["evaluation_cutoff"],
                         "generated_input_sha256": input_digest(bids, risks),
                         "interpretation": "Synthetic test inputs, not observed bids or estimated market probabilities."}}


def record_applied_example(case, example: dict) -> None:
    applied = input_digest(case.context["bids"], case.context["scenarios"])
    case.context.pop("demonstration", None)
    case.context["tender_example"] = {**example["metadata"], "applied_input_sha256": applied,
        "edited_before_apply": applied != example["metadata"]["generated_input_sha256"],
        "applied_auction_clock": deepcopy(case.context.get("auction_clock")),
        "applied_evaluation_cutoff": case.context["evaluation_cutoff"],
        "applied_pi_selected_bid_id": case.context.get("pi_selected_bid_id")}
    case._invalidate()
