from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pilog_cfr_dss.application.market_case import new_market_case, seed_demo_bids, apply_market, apply_profile, catalog, compare_profiles
from pilog_cfr_dss.sources.fearnpulse import latest_saved
from pilog_cfr_dss.orchestration.iteration_04 import evaluate
from pilog_cfr_dss.reporting.iteration_04 import commercial_brief

ROOT = Path(__file__).resolve().parents[2]


class MarketPipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.drafts, self.runs = self.root / "drafts", self.root / "runs"
        self.snapshot = latest_saved(ROOT)
        self.case = new_market_case(ROOT, self.snapshot)

    def evaluate_case(self, case=None, no_go=False):
        case = case or self.case
        case.prepare(self.drafts); case.fix_freight(self.drafts); seed_demo_bids(case, ROOT, no_go=no_go)
        return case.evaluate(self.drafts, self.runs)

    def test_four_profiles_complete_end_to_end_without_baltic(self):
        for profile in catalog(ROOT)["profiles"]:
            with self.subTest(profile=profile["profile_id"]):
                case = new_market_case(ROOT, self.snapshot, profile["profile_id"])
                result = self.evaluate_case(case)
                self.assertEqual(result["recommendation"]["action"], "GO")
                self.assertEqual(result["case"]["dwt_mt"], profile["fields"]["dwt_mt"])
                self.assertNotIn("baltic", json.dumps(result["input_lineage"]).lower())
                self.assertEqual(result["pricing"]["basis"]["target_tce"]["value"], self.snapshot["tc_rates"][profile["market_family"]]["value"])
                self.assertEqual(result["report_version"], "I4-BRIEF.8")

    def test_no_go_still_gate_a_floor_not_fake_economic_rejection(self):
        result = self.evaluate_case(no_go=True)
        self.assertEqual(result["recommendation"]["action"], "NO_GO")
        self.assertEqual(result["recommendation"]["gate_b"], "NOT_EVALUATED")

    def test_snapshot_replay_offline_preserves_prices_and_embedded_payloads(self):
        result = self.evaluate_case()
        with patch("pilog_cfr_dss.sources.fearnpulse.urlopen", side_effect=AssertionError("must replay offline")):
            replay = evaluate(self.case.run_dir / "input_snapshot/case_fixture.json")
        for key in ("baseline", "tender", "commercial_financials"):
            self.assertEqual(result[key], replay[key])
        for name, raw in self.snapshot["raw_payloads"].items():
            captured = (self.case.run_dir / "input_snapshot" / name).read_bytes()
            self.assertEqual(hashlib.sha256(captured).hexdigest(), self.snapshot["payload_hashes"][name])
            self.assertEqual(captured, raw.encode("utf-8"))

    def test_fixed_timestamp_survives_alpha_edit_and_new_evaluation(self):
        first = self.evaluate_case()
        fixed = deepcopy(self.case.context["freight_tender"])
        bids = deepcopy(self.case.context["bids"]); bids[-1]["alpha_usd_mt"] = "50"
        self.case.apply_tender(bids, self.case.context["evaluation_cutoff"])
        second = self.case.evaluate(self.drafts, self.runs)
        self.assertEqual(fixed, self.case.context["freight_tender"])
        self.assertEqual(first["price_records"]["freight"]["fixed_at"], second["price_records"]["freight"]["fixed_at"])
        self.assertNotEqual(first["pricing"]["calculated_at"], second["pricing"]["calculated_at"])
        self.assertEqual(first["baseline"], second["baseline"])

    def test_refresh_never_reprices_fixed_case(self):
        self.evaluate_case()
        with self.assertRaisesRegex(ValueError, "BASIS_FIXED"):
            apply_market(self.case, self.snapshot)
        revised = self.case.revise()
        self.assertFalse(revised.fixed)
        self.assertEqual(revised.context["bids"], [])

    def test_tampered_source_record_fails_safe(self):
        self.case.context["market_snapshot"]["tc_rates"]["Handysize"]["value"] = "1"
        result = evaluate(self.case.save(self.drafts))
        self.assertIn("DATA_ISSUE", result["recommendation"]["reason_codes"])
        self.assertTrue(any("MARKET_SNAPSHOT_MISMATCH" in reason for reason in result["recommendation"]["reason_codes"]))

    def test_unmarked_bound_cost_override_is_not_accepted_as_source_data(self):
        next(r for r in self.case.rows if r["key"] == "fo_price_usd_mt")["value"] = "1"
        result = evaluate(self.case.save(self.drafts))
        self.assertTrue(any("BUNKER_SOURCE_BINDING_MISMATCH" in reason for reason in result["recommendation"]["reason_codes"]))

    def test_manual_target_removes_source_date_and_is_explicit(self):
        self.case.apply_inputs({}, target_tce="16000", observations={}, oe_hps="420")
        target = self.case.context["pricing"]["target_tce"]
        self.assertEqual(target["source_status"], "simulation_only_user_input")
        self.assertNotIn("source_observed_on", target)
        self.assertNotIn("source_snapshot_id", target)
        self.assertEqual(self.evaluate_case()["recommendation"]["action"], "GO")

    def test_comparison_does_not_mutate_selected_case_or_reprice(self):
        fingerprint = self.case.fingerprint
        rows = compare_profiles(self.case, ROOT, self.drafts)
        self.assertEqual(len(rows), 4)
        self.assertEqual(self.case.fingerprint, fingerprint)
        self.assertFalse(self.case.fixed)
        self.assertNotEqual(rows[0]["baseline"]["bunker_usd"], rows[1]["baseline"]["bunker_usd"])
        self.assertTrue(next(r for r in rows if r["sheet"] == "Godau")["class_proxy"])

    def test_scheduled_case_requires_time_and_excludes_closing_instant(self):
        result = self.evaluate_case()
        bids = deepcopy(self.case.context["bids"])
        bids[-1].pop("submitted_at")
        self.case.apply_tender(bids, self.case.context["evaluation_cutoff"])
        result = self.case.evaluate(self.drafts, self.runs)
        self.assertIn("SCHEDULED_BID_REQUIRES_SUBMITTED_AT", result["recommendation"]["reason_codes"])

    def test_brief_contains_actual_price_dates_and_fixed_time(self):
        result = self.evaluate_case()
        text = commercial_brief(result)
        self.assertIn("Waktu dan sumber harga", text)
        self.assertIn("2026-07-01", text)
        self.assertIn("2026-10-21", text)
        self.assertIn("3 menit", text)
        self.assertTrue(all(row["calculated_at"] and row["freight_fixed_at"] for row in result["price_records"]["bids"]))
