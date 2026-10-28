import unittest
from decimal import Decimal as D
from pathlib import Path
from pilog_cfr_dss.calculations.pricing_04 import required_freight, economics, decision_metrics, commercial_financials
from pilog_cfr_dss.calculations.voyage_04 import voyage
from pilog_cfr_dss.calculations.tender_04 import bid_prices, index_prices, minimum_alpha
from pilog_cfr_dss.validation.iteration_04 import load_case

ROOT = Path(__file__).resolve().parents[2]


class I4CalculationTests(unittest.TestCase):
    def financials(self, rate=D(5), fee=D("0.1"), quantity=D(100)):
        baseline = economics({"voyage_expenses_usd": D(100), "total_cash_cost_usd": D(150), "total_days": D(10)}, rate, quantity, fee)
        bids = [{"bid_id": "test", "buyer_id": "buyer", "fob_usd_mt": D(20),
                 "freight_usd_mt": rate, "cfr_usd_mt": D(20) + rate}]
        return commercial_financials(quantity, bids, baseline), baseline, bids

    def test_financial_summary_separates_commodity_freight_and_combined_quote(self):
        result, baseline, _ = self.financials()
        row, pilog = result["bid_amounts"][0], result["pilog"]
        self.assertEqual(row["pi_goods_gross_revenue_usd"], D(20) * D(100))
        self.assertEqual(row["buyer_cfr_offer_value_usd"], row["pi_goods_gross_revenue_usd"] + pilog["gross_revenue_usd"])
        self.assertEqual(row["pilog_gross_freight_revenue_usd"], baseline["revenue_usd"])
        self.assertIsNone(result["pi"]["goods_cost_usd"])
        self.assertIsNone(result["pi"]["net_result_usd"])

    def test_net_after_voyage_is_not_net_after_commission(self):
        result, baseline, _ = self.financials()
        p = result["pilog"]
        self.assertEqual(p["revenue_after_commission_usd"], baseline["net_revenue_usd"])
        self.assertNotEqual(p["net_after_voyage_usd"], p["revenue_after_commission_usd"])
        self.assertEqual(p["net_after_voyage_usd"], p["gross_revenue_usd"] - p["voyage_cost_usd"] - p["commission_usd"])
        self.assertEqual(p["total_deductions_usd"], p["voyage_cost_usd"] + p["commission_usd"])

    def test_financial_summary_allows_loss_and_exact_zero(self):
        for rate in (D(1), D("1.5")):
            result, baseline, _ = self.financials(rate, D(0))
            self.assertEqual(result["pilog"]["net_after_voyage_usd"], baseline["contribution_usd"])
            self.assertLessEqual(result["pilog"]["net_after_voyage_usd"], D(0))

    def test_financial_summary_rejects_invalid_quantity_missing_nonfinite(self):
        _, baseline, bids = self.financials()
        for quantity, base in [(D(0), baseline), (None, baseline), (D(100), {}),
                               (D(100), {**baseline, "contribution_usd": D("NaN")}),
                               (D(100), {**baseline, "commission_usd": D(-1)})]:
            with self.subTest(quantity=quantity, base=base), self.assertRaises(ValueError):
                commercial_financials(quantity, bids, base)

    def test_financial_summary_rejects_missing_or_invalid_bid_price(self):
        _, baseline, bids = self.financials()
        for price in (None, D(-1), D("Infinity"), "20"):
            with self.subTest(price=price), self.assertRaises(ValueError):
                commercial_financials(D(100), [{**bids[0], "fob_usd_mt": price}], baseline)

    def test_financial_summary_empty_bids_does_not_invent_commodity_revenue(self):
        _, baseline, _ = self.financials()
        result = commercial_financials(D(100), [], baseline)
        self.assertEqual(result["bid_amounts"], [])
        self.assertIsNone(result["pi"]["net_result_usd"])

    def test_financial_summary_does_not_mutate_inputs(self):
        _, baseline, bids = self.financials()
        before = str((baseline, bids))
        commercial_financials(D(100), bids, baseline)
        self.assertEqual(str((baseline, bids)), before)

    def test_one_way_days_full_port_and_no_return(self):
        case, _ = load_case(ROOT / "data/processed/i4_context.json")
        v = voyage(case)
        self.assertEqual(v["sea_days"], D("13.5625"))
        self.assertEqual(v["loading_days"], D(6))
        self.assertEqual(v["discharge_days"], D(6))
        self.assertEqual(v["total_days"], D("25.5625"))
        self.assertEqual(v["fo_mt"], D("244.125"))
        self.assertEqual(v["port_other_usd"], D(200000))
        self.assertEqual(v["total_cash_cost_usd"], D("511334.80125"))

    def test_pricing_commission_inverse_before_running(self):
        rate = required_freight(D(1000), D(10), D(100), D(100), D("0.2"))
        self.assertEqual(rate, D(25))
        costs = {"voyage_expenses_usd": D(1000), "total_cash_cost_usd": D(1500), "total_days": D(10)}
        e = economics(costs, rate, D(100), D("0.2"))
        self.assertEqual(e["tce_before_running_usd_day"], D(100))
        self.assertEqual(e["contribution_usd"], D(500))
        self.assertEqual(e["revenue_usd"], D(2500))

    def test_pricing_invalid_boundaries(self):
        for q, days, fee, target in [(0, 10, "0.2", 100), (100, 0, "0.2", 100), (100, 10, "1", 100), (100, 10, "0", -1)]:
            with self.subTest(q=q, days=days, fee=fee, target=target), self.assertRaises(ValueError):
                required_freight(D(1000), D(days), D(q), D(target), D(fee))
        with self.assertRaises(ValueError):
            required_freight(D("NaN"), D(10), D(100), D(100), D(0))

    def test_contribution_zero_and_negative(self):
        costs = {"voyage_expenses_usd": D(100), "total_cash_cost_usd": D(150), "total_days": D(10)}
        self.assertEqual(economics(costs, D("1.5"), D(100), D(0))["contribution_usd"], D(0))
        self.assertEqual(economics(costs, D(1), D(100), D(0))["contribution_usd"], D(-50))

    def test_shocks_change_cost_not_quantity_or_extra_sea_leg(self):
        case, _ = load_case(ROOT / "data/processed/i4_context.json")
        base, shock = voyage(case), voyage(case, D("0.25"), D(3))
        self.assertEqual(base["sea_days"], shock["sea_days"])
        self.assertEqual(shock["total_days"] - base["total_days"], D(3))
        self.assertEqual(shock["port_do_mt"] - base["port_do_mt"], D("10.08"))
        self.assertGreater(shock["bunker_usd"], base["bunker_usd"])
        with self.assertRaises(ValueError):
            voyage(case, D(-1))

    def test_index_and_alpha_once(self):
        index = index_prices({"argus": {"low": "415", "high": "425"}, "fertecon": {"low": "410", "high": "410"}})
        self.assertEqual(index["index_usd_mt"], D(415))
        r = bid_prices(D(415), D(420), D(25), [{"bid_id": "x", "alpha_usd_mt": "5"}])[0]
        self.assertEqual(r["fob_usd_mt"], D(420))
        self.assertEqual(r["cfr_usd_mt"], D(445))
        self.assertEqual(r["oe_gap_usd_mt"], D(0))
        self.assertEqual(r["freight_usd_mt"], D(25))
        self.assertEqual(r["floor_shortfall_usd_mt"], D(0))

    def metrics(self, contribution="188856.76125", running="5612", port_do="3.36"):
        return decision_metrics({"contribution_usd": D(contribution), "total_cash_cost_usd": D("511334.80125"),
                                 "commission_usd": D("46679.4375")}, D(30000), D("0.0625"),
                                D(running), D(port_do), D(701))

    def test_metrics_match_independent_review_and_commission_break_even(self):
        m = self.metrics()
        self.assertEqual(m["contribution_per_mt_usd"], D("6.295225375"))
        self.assertEqual(m["incremental_port_day_usd"], D("7967.36"))
        self.assertAlmostEqual(m["freight_break_even_usd_mt"], D("18.18079293333333333333333333"), places=22)
        self.assertAlmostEqual(m["additional_port_days_to_break_even"], D("23.70380668753514338501084424"), places=22)
        costs = {"total_cash_cost_usd": D("511334.80125"), "voyage_expenses_usd": D("367878.05125"), "total_days": D("25.5625")}
        be = economics(costs, m["freight_break_even_usd_mt"], D(30000), D("0.0625"))
        self.assertAlmostEqual(be["contribution_usd"], D(0), places=20)
        self.assertFalse(m["is_gate"])

    def test_metrics_zero_baseline_is_impas_not_positive_buffer(self):
        m = self.metrics("0")
        self.assertEqual(m["additional_port_days_to_break_even"], D(0))
        self.assertEqual(m["delay_buffer_status"], "BASELINE_BREAK_EVEN")

    def test_metrics_negative_baseline_has_no_negative_delay_allowance(self):
        m = self.metrics("-1")
        self.assertIsNone(m["additional_port_days_to_break_even"])
        self.assertEqual(m["delay_buffer_status"], "BASELINE_ALREADY_NEGATIVE")

    def test_metrics_zero_daily_cost_does_not_imply_infinite_safety(self):
        for contribution in ("0", "1"):
            m = self.metrics(contribution, "0", "0")
            self.assertIsNone(m["additional_port_days_to_break_even"])
            self.assertEqual(m["delay_buffer_status"], "NO_INCREMENTAL_DAILY_COST_MODELLED")

    def test_metrics_missing_or_invalid_input_fails_not_defaults(self):
        valid = {"contribution_usd": D(1), "total_cash_cost_usd": D(1), "commission_usd": D(0)}
        for baseline, q, fee, running in [({}, D(1), D(0), D(1)), (valid, D(0), D(0), D(1)),
                                          (valid, D(1), D(1), D(1)), (valid, D(1), D(0), None),
                                          (valid, D(1), D(0), D("NaN")), (valid, D(1), D(0), D(-1))]:
            with self.subTest(baseline=baseline, q=q, fee=fee, running=running), self.assertRaises(ValueError):
                decision_metrics(baseline, q, fee, running, D(0), D(1))

    def test_alpha_minimum_not_clamped_and_gap_is_fob_not_cfr(self):
        for floor in (D(410), D(415), D(420)):
            alpha = minimum_alpha(D(415), floor)
            row = bid_prices(D(415), floor, D(25), [{"alpha_usd_mt": str(alpha)}])[0]
            self.assertEqual(row["oe_gap_usd_mt"], D(0))
            self.assertEqual(row["fob_usd_mt"], floor)
        self.assertLess(minimum_alpha(D(415), D(410)), 0)
        r = bid_prices(D(415), D(420), D(25), [{"alpha_usd_mt": "-14"}])[0]
        self.assertEqual(r["floor_shortfall_usd_mt"], D(19))
        with self.assertRaises(ValueError):
            minimum_alpha(D("NaN"), D(420))
