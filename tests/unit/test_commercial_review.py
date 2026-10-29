from decimal import Decimal as D
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from pilog_cfr_dss.calculations.pricing_04 import economics
from pilog_cfr_dss.calculations.commercial_review import commercial_review, net_daily, demo_port_cost


class CommercialReviewMathTests(unittest.TestCase):
    def setUp(self):
        self.cost = {"voyage_expenses_usd": D(80), "total_cash_cost_usd": D(100), "total_days": D(10),
                     "bunker_usd": D(50), "port_other_usd": D(30), "running_usd": D(20)}
        self.quote = economics(self.cost, D(12), D(10), D(0))

    def test_loss_recovery_and_driver_units(self):
        current = economics({**self.cost, "voyage_expenses_usd": D(110), "total_cash_cost_usd": D(130), "port_other_usd": D(60)}, D(12), D(10), D(0))
        result = commercial_review(current, self.quote, D(10), D(0), D(4), D(13))
        self.assertEqual(result["loss_to_recover_usd"], D(10))
        self.assertEqual(result["hypothetical_freight_increase_usd_mt"], D(1))
        self.assertEqual(result["current_contribution_per_day_usd"], D(-1))
        self.assertEqual(result["contribution_change_usd"], D(-30))
        self.assertEqual(sum(row["change_usd"] for row in result["drivers"]), D(30))

    def test_positive_or_zero_result_does_not_invent_recovery_cost(self):
        for rate in (D(10), D(12)):
            current = economics(self.cost, rate, D(10), D(0))
            result = commercial_review(current, self.quote, D(10), D(0), D(4), D(10))
            self.assertEqual(result["loss_to_recover_usd"], 0)
            self.assertEqual(result["hypothetical_freight_increase_usd_mt"], 0)

    def test_break_even_quote_is_ceiled_to_four_decimals(self):
        result = commercial_review(self.quote, self.quote, D(10), D(0), D(4), D("12.00001"))
        self.assertEqual(result["break_even_offer_usd_mt"], D("12.0001"))
        current = {**self.quote, "contribution_usd": D("-10.001")}
        result = commercial_review(current, self.quote, D(10), D(0), D(4), D(13))
        self.assertEqual(result["minimum_cost_reduction_usd"], D("10.01"))

    def test_invalid_denominator_and_nonfinite_value_rejected(self):
        for quantity, fee in ((D(0), D(0)), (D(10), D(1)), (D("NaN"), D(0))):
            with self.subTest(quantity=quantity, fee=fee), self.assertRaises(ValueError):
                commercial_review(self.quote, self.quote, quantity, fee, D(4), D(10))
        with self.assertRaises(ValueError):
            net_daily({**self.quote, "total_days": D(0)})

    def test_demo_cost_is_explicitly_sufficient_for_each_profile(self):
        self.assertEqual(demo_port_cost(D(200000), D(227199)), D(450000))
        self.assertGreater(demo_port_cost(D(200000), D(303888)), D(503888))
