from __future__ import annotations

import unittest
from decimal import Decimal

from pilog_cfr_dss.calculations.tender import average_two_publishers, midpoint, tender_bids


class Iteration03TenderMathTests(unittest.TestCase):
    def test_midpoint_and_two_publisher_average(self) -> None:
        argus = midpoint(Decimal("400"), Decimal("420"))
        fertecon = midpoint(Decimal("410"), Decimal("430"))
        self.assertEqual(average_two_publishers(argus, fertecon), Decimal("415"))
        with self.assertRaisesRegex(ValueError, "INVALID_MARKET_RANGE"):
            midpoint(Decimal("420"), Decimal("400"))

    def test_oe_floor_includes_equality_and_does_not_use_alpha_sign(self) -> None:
        bids = tender_bids(Decimal("410"), Decimal("415"), [
            {"bid_id": "EQ", "round": 1, "buyer_id": "B1", "alpha_usd_mt": "5", "source_status": "simulation_only_synthetic"},
            {"bid_id": "NEG", "round": 2, "buyer_id": "B2", "alpha_usd_mt": "-10", "source_status": "simulation_only_synthetic"},
        ])
        self.assertTrue(bids[0]["eligible_oe_floor"])
        self.assertEqual(bids[0]["oe_gap_usd_mt"], "0")
        self.assertFalse(bids[1]["eligible_oe_floor"])
        self.assertEqual(bids[1]["fob_usd_mt"], "400")


if __name__ == "__main__":
    unittest.main()
