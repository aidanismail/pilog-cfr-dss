from copy import deepcopy
from decimal import Decimal as D, localcontext
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from pilog_cfr_dss.application.interactive_case import InteractiveCase
from pilog_cfr_dss.application.market_case import new_market_case, seed_demo_bids, compare_profiles, demo_case
from pilog_cfr_dss.sources.fearnpulse import latest_saved
from pilog_cfr_dss.orchestration.iteration_04 import evaluate
from pilog_cfr_dss.reporting.iteration_04 import commercial_brief


class CommercialReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshot = latest_saved(ROOT)
        cls.template = new_market_case(ROOT, cls.snapshot)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.drafts, self.runs = Path(self.temp.name) / "drafts", Path(self.temp.name) / "runs"
        self.case = InteractiveCase(deepcopy(self.template.context), deepcopy(self.template.rows))

    def fix_and_bid(self, rate=None, reason=""):
        self.case.prepare(self.drafts); self.case.fix_freight(self.drafts, rate, reason)
        seed_demo_bids(self.case, ROOT)
        return self.case

    def result(self, case=None):
        return (case or self.case).evaluate(self.drafts, self.runs)

    def test_highest_bid_passes_gate_a_but_higher_costs_fail_gate_b(self):
        original = self.fix_and_bid(); before = self.result()
        signature = original.fingerprint; quote = deepcopy(original.context["freight_tender"])
        changed = original.reforecast_costs({"port_other_total_usd": "450000"}, "Synthetic port cost update")
        result = self.result(changed)
        self.assertEqual(result["recommendation"]["action"], "NO_GO")
        self.assertEqual((result["recommendation"]["gate_a"], result["recommendation"]["gate_b"]), ("PASS", "FAIL"))
        self.assertIn("NEGATIVE_BASELINE_CONTRIBUTION", result["recommendation"]["reason_codes"])
        self.assertEqual(before["tender"], result["tender"])
        self.assertEqual(quote, changed.context["freight_tender"])
        self.assertEqual(signature, original.fingerprint)
        self.assertEqual(result["tender"]["candidate_bid_ids"], ["R3-B1"])
        self.assertGreater(D(result["baseline"]["revenue_usd"]), 0)
        with localcontext() as precision:
            precision.prec = 40
            self.assertEqual(D(result["baseline"]["contribution_usd"]), D(before["baseline"]["contribution_usd"]) - D("250000"))
        self.assertEqual(D(result["commercial_review"]["cost_increase_usd"]), D("250000"))
        self.assertGreater(D(result["commercial_review"]["loss_to_recover_usd"]), 0)

    def test_reforecast_requires_fixed_quote_and_reason(self):
        with self.assertRaisesRegex(ValueError, "FREIGHT_NOT_FIXED"):
            self.case.reforecast_costs({}, "test")
        self.fix_and_bid()
        with self.assertRaisesRegex(ValueError, "REASON_REQUIRED"):
            self.case.reforecast_costs({}, " ")

    def test_invalid_reforecasts_leave_original_unchanged(self):
        self.fix_and_bid(); signature = self.case.fingerprint
        for edits in ({"cargo_mt": "1"}, {"distance_nm": "1"}, {"broker_fraction": "0.1"},
                      {"port_other_total_usd": "-1"}, {"speed_knots": "0"},
                      {"fo_price_usd_mt": "NaN"}, {"waiting_days": ""}):
            with self.subTest(edits=edits), self.assertRaises(ValueError):
                self.case.reforecast_costs(edits, "test invalid values")
            self.assertEqual(self.case.fingerprint, signature)

    def test_forecast_cannot_be_rebound_to_another_quote_or_changed_source_rows(self):
        self.fix_and_bid()
        for kind in ("quote", "rows", "unit"):
            changed = self.case.reforecast_costs({"waiting_days": "3"}, "test binding")
            if kind == "quote": changed.context["freight_tender"]["value"] = "99"
            elif kind == "rows": next(row for row in changed.rows if row["key"] == "port_other_total_usd")["value"] = "201000"
            else: changed.context["cost_forecast"]["overrides"]["waiting_days"]["unit"] = "hour"
            result = evaluate(changed.save(self.drafts))
            self.assertIn("DATA_ISSUE", result["recommendation"]["reason_codes"])
            self.assertTrue(any("COST_FORECAST" in r for r in result["recommendation"]["reason_codes"]))

    def test_snapshot_replay_preserves_reforecast_and_decision_offline(self):
        self.fix_and_bid()
        changed = self.case.reforecast_costs({"port_other_total_usd": "450000"}, "test replay")
        result = self.result(changed)
        with patch("pilog_cfr_dss.sources.fearnpulse.urlopen", side_effect=AssertionError("offline")):
            replay = evaluate(changed.run_dir / "input_snapshot/case_fixture.json")
        for key in ("baseline", "commercial_review", "tender", "commercial_financials"):
            self.assertEqual(result[key], replay[key])

    def test_reverting_latest_estimate_recovers_go_without_repricing(self):
        self.fix_and_bid()
        changed = self.case.reforecast_costs({"port_other_total_usd": "450000"}, "cost rises")
        restored = changed.reforecast_costs({"port_other_total_usd": self.case.values()["port_other_total_usd"]}, "cost returns")
        self.assertEqual(self.result(restored)["recommendation"]["action"], "GO")
        self.assertEqual(restored.context["freight_tender"], self.case.context["freight_tender"])
        self.assertEqual(restored.context["cost_forecast"]["parent_forecast_id"], changed.context["cost_forecast"]["forecast_id"])

    def test_new_quote_revision_promotes_latest_costs_and_discards_old_bids(self):
        self.fix_and_bid()
        changed = self.case.reforecast_costs({"port_other_total_usd": "450000", "fo_price_usd_mt": "500"}, "new estimate")
        revised = changed.revise()
        self.assertFalse(revised.fixed); self.assertEqual(revised.context["bids"], [])
        self.assertNotIn("cost_forecast", revised.context)
        self.assertEqual(revised.values()["port_other_total_usd"], "450000")
        self.assertIsNotNone(revised.prepare(self.drafts))

    def test_manual_offer_below_break_even_can_fail_before_any_cost_change(self):
        self.fix_and_bid("10", "Synthetic low offer for testing")
        result = self.result()
        self.assertEqual((result["recommendation"]["gate_a"], result["recommendation"]["gate_b"]), ("PASS", "FAIL"))
        self.assertEqual(result["pricing"]["freight_tender_usd_mt"], "10")
        self.assertEqual(D(result["commercial_review"]["cost_increase_usd"]), 0)
        self.assertGreater(D(result["commercial_review"]["loss_to_recover_usd"]), 0)
        self.assertEqual(result["commercial_review"]["market_acceptance"], "NOT_RECORDED")

    def test_manual_offer_needs_reason_and_never_accepts_nonfinite_or_negative(self):
        self.case.prepare(self.drafts)
        for rate in ("10", "NaN", "-1"):
            with self.subTest(rate=rate), self.assertRaises(ValueError):
                self.case.fix_freight(self.drafts, rate)
            self.assertFalse(self.case.fixed)

    def test_same_freight_comparison_does_not_mutate_selected_case(self):
        self.fix_and_bid(); signature = self.case.fingerprint
        rows = compare_profiles(self.case, ROOT, self.drafts, "25")
        self.assertEqual(signature, self.case.fingerprint)
        self.assertEqual(len(rows), 4)
        self.assertEqual({row["common_freight_usd_mt"] for row in rows}, {"25"})
        self.assertEqual(len({row["common_rate_economics"]["revenue_usd"] for row in rows}), 1)
        self.assertTrue(all(not row["automatic_vessel_selection"] for row in rows))
        self.assertLess(D(rows[1]["common_rate_economics"]["total_cash_cost_usd"]), D(rows[2]["common_rate_economics"]["total_cash_cost_usd"]))

    def test_combined_risk_is_calculated_and_does_not_veto_baseline(self):
        self.fix_and_bid(); result = self.result()
        scenarios = {row["scenario_id"]: row for row in result["scenarios"]}
        self.assertIn("fuel_and_delay", scenarios)
        self.assertLess(D(scenarios["fuel_and_delay"]["economics"]["contribution_usd"]), D(scenarios["port_delay"]["economics"]["contribution_usd"]))
        self.assertEqual(result["recommendation"]["action"], "GO")

    def test_capacity_and_negative_economics_both_disclosed(self):
        next(row for row in self.case.rows if row["key"] == "cargo_mt")["value"] = "40000"
        self.fix_and_bid("1", "Synthetic capacity/economic failure")
        result = self.result()
        self.assertEqual(result["recommendation"]["brief_context"]["cause"], "VESSEL_AND_ECONOMICS")
        self.assertFalse(result["recommendation"]["vessel_screen"]["passed"])
        self.assertIn("NEGATIVE_BASELINE_CONTRIBUTION", result["recommendation"]["reason_codes"])

    def test_no_go_brief_quantifies_loss_and_recovery_without_repricing(self):
        self.fix_and_bid()
        changed = self.case.reforecast_costs({"port_other_total_usd": "450000"}, "Synthetic revised port budget")
        result = self.result(changed); text = commercial_brief(result)
        self.assertIn("Bid barang yang tertinggi/lolos PI tidak menghilangkan kerugian freight PILOG", text)
        self.assertIn("### Dasar perubahan hasil", text)
        self.assertIn("Kurangi biaya", text)
        self.assertIn("hitungan hipotetis", text)
        self.assertIn("### Asal tarif", text)
        self.assertEqual(result["report_version"], "I4-BRIEF.8")
        self.assertEqual(len([line for line in text.splitlines() if line.startswith('## ')]), 5)

    def test_floor_no_go_not_confused_with_negative_pilog_contribution(self):
        self.fix_and_bid(); seed_demo_bids(self.case, ROOT, no_go=True)
        result = self.result(); text = commercial_brief(result)
        self.assertEqual(result["recommendation"]["gate_a"], "FAIL")
        self.assertEqual(result["recommendation"]["gate_b"], "NOT_EVALUATED")
        self.assertNotIn("Kurangi biaya yang benar-benar", text)
        self.assertIn("Gate B belum dievaluasi", text)

    def test_zero_contribution_passes_but_one_dollar_loss_fails_same_quote(self):
        self.case.apply_inputs({"port_other_total_usd": "600000", "sea_fo_mt_day": "0", "sea_do_mt_day": "0",
            "port_do_mt_day": "0", "running_usd_day": "0"}, target_tce="14500", observations={}, oe_hps="420")
        self.fix_and_bid("20", "Synthetic exact break-even quote")
        result = self.result()
        self.assertEqual(D(result["baseline"]["contribution_usd"]), 0)
        self.assertEqual(result["recommendation"]["action"], "GO")
        changed = self.case.reforecast_costs({"port_other_total_usd": "600001"}, "one dollar extra")
        self.assertEqual(self.result(changed)["recommendation"]["action"], "NO_GO")

    def test_demo_economic_no_go_works_for_all_four_profiles(self):
        for profile in ("ve_sheet1", "ve_aqaba", "ve_sby", "ve_godau"):
            with self.subTest(profile=profile):
                case = demo_case(ROOT, self.snapshot, self.drafts, "no-go-economics", profile)
                result = self.result(case)
                self.assertEqual((result["recommendation"]["gate_a"], result["recommendation"]["gate_b"]), ("PASS", "FAIL"))
                self.assertEqual(result["recommendation"]["action"], "NO_GO")

    def test_presentation_pair_can_share_exact_same_quote_and_bids(self):
        anchor = demo_case(ROOT, self.snapshot, self.drafts)
        go = demo_case(ROOT, self.snapshot, self.drafts, "go", base_case=anchor)
        no_go = demo_case(ROOT, self.snapshot, self.drafts, "no-go-economics", base_case=anchor)
        self.assertEqual(go.context["freight_tender"], no_go.context["freight_tender"])
        self.assertEqual(go.context["bids"], no_go.context["bids"])
        self.assertEqual(go.rows, no_go.rows)
        self.assertEqual(self.result(go)["recommendation"]["action"], "GO")
        self.assertEqual(self.result(no_go)["recommendation"]["action"], "NO_GO")

    def test_prescribed_break_even_actions_really_recover_nonnegative_result(self):
        self.fix_and_bid()
        changed = self.case.reforecast_costs({"port_other_total_usd": "450000"}, "Synthetic loss case")
        result = self.result(changed)
        review = result["commercial_review"]
        reduced = D("450000") - D(review["minimum_cost_reduction_usd"])
        recovered = changed.reforecast_costs({"port_other_total_usd": str(reduced)}, "Synthetic approved cost reduction")
        self.assertEqual(self.result(recovered)["recommendation"]["action"], "GO")
        self.assertEqual(recovered.context["freight_tender"], changed.context["freight_tender"])
        repriced = changed.revise(); repriced.prepare(self.drafts)
        repriced.fix_freight(self.drafts, review["break_even_offer_usd_mt"], "Synthetic explicit new break-even offer")
        seed_demo_bids(repriced, ROOT)
        self.assertEqual(self.result(repriced)["recommendation"]["action"], "GO")
        self.assertNotEqual(repriced.context["freight_tender"]["price_id"], changed.context["freight_tender"]["price_id"])

    def test_two_decimal_display_does_not_change_raw_quote_or_decision(self):
        from copy import deepcopy
        self.fix_and_bid()
        result = self.result()
        before = deepcopy(result)
        text = commercial_brief(result)
        self.assertIn("25,45 USD/MT", text)
        self.assertNotIn("25.4513 USD/MT", text)
        self.assertEqual(result, before)
        self.assertEqual(result["pricing"]["freight_tender_usd_mt"], "25.4513")
        self.assertEqual(result["recommendation"]["action"], "GO")

    def test_minimum_two_decimal_price_in_brief_recovers_without_false_go(self):
        from pilog_cfr_dss.reporting.formatting import number_text
        self.fix_and_bid()
        changed = self.case.reforecast_costs({"port_other_total_usd": "450000"}, "Synthetic rounding boundary")
        result = self.result(changed)
        display = number_text(result["commercial_review"]["break_even_offer_usd_mt"], minimum=True)
        self.assertIn(display + " USD/MT", commercial_brief(result))
        rate = display.replace(".", "").replace(",", ".")
        revised = changed.revise(); revised.prepare(self.drafts)
        revised.fix_freight(self.drafts, rate, "Synthetic explicit rounded break-even offer")
        seed_demo_bids(revised, ROOT)
        self.assertEqual(self.result(revised)["recommendation"]["action"], "GO")
        self.assertEqual(self.result(changed)["recommendation"]["action"], "NO_GO")
