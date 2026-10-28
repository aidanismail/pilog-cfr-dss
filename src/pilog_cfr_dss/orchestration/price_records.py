"""Time and identity metadata for prices already calculated by the engine."""
from datetime import datetime, timezone


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def price_records(report: dict, context: dict, calculated_at: str) -> dict:
    fixed = context.get("freight_tender") or {}
    snapshot = context.get("market_snapshot") or {}
    common = {"calculated_at": calculated_at, "market_snapshot_id": snapshot.get("snapshot_id"),
              "profile_id": context.get("vessel_profile", {}).get("profile_id"),
              "market_fetched_at": snapshot.get("fetched_at"), "actor_id": None,
              "actor_type": "local_session", "actor_role": None}
    records = {"version": "PRICE.1",
               "index": {**common, "price_type": "computed_commodity_index", "value": report["index"]["index_usd_mt"], "unit": "USD/MT",
                         "source_dates": {key: value.get("observation_date") for key, value in context["market_index"].items()}},
               "target_tce": {**common, "price_type": "market_reference_or_manual_input", **context["pricing"]["target_tce"]},
               "oe_hps": {**common, **context["oe_hps"], "price_type": "PI_floor_input", "calculated_at": None,
                          "used_at": calculated_at, "source_observed_on": context["oe_hps"].get("observation_date")},
               "freight": {**common, "value": report["pricing"]["freight_tender_usd_mt"], "unit": "USD/MT",
                           "price_id": fixed.get("price_id"), "fixed_at": fixed.get("fixed_at"),
                           "original_calculated_at": fixed.get("calculated_at"), "price_type": "fixed_tender" if fixed else "indication"},
               "bids": []}
    for bid in report["tender"]["bids"]:
        records["bids"].append({**common, "bid_id": bid["bid_id"], "buyer_id": bid["buyer_id"],
                              "submitted_at": bid.get("submitted_at"), "unit": "USD/MT",
                              "alpha": bid["alpha_usd_mt"], "fob": bid["fob_usd_mt"], "cfr": bid["cfr_usd_mt"],
                              "freight_price_id": fixed.get("price_id"), "freight_fixed_at": fixed.get("fixed_at")})
    return records
