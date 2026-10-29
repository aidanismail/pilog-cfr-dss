import unittest
import tempfile
from copy import deepcopy
from pathlib import Path

from pilog_cfr_dss.application.interactive_case import InteractiveCase
from pilog_cfr_dss.orchestration.iteration_04 import evaluate


ROOT = Path(__file__).resolve().parents[2]
GO = ROOT / "data/processed/i4_context.json"
NO = ROOT / "data/processed/i4_no_go.json"


class UIEngineParityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name)
        self.drafts = self.output / "ui_cases"
        self.runs = self.output / "runs"
        self.case = InteractiveCase.read(GO)

    def test_go_and_no_go_match_cli_and_preparation(self):
        for path in (GO, NO):
            with self.subTest(path=path.name):
                case = InteractiveCase.read(path)
                prepared = case.prepare(self.drafts)
                expected = evaluate(path)
                actual = case.evaluate(self.drafts, self.runs)
                for field in ("baseline", "metrics", "tender", "recommendation", "scenarios", "commercial_financials", "pricing"):
                    self.assertEqual(actual[field], expected[field], field)
                self.assertEqual(prepared["baseline"], expected["baseline"])

    def test_alpha_only_changes_pi_not_pilog(self):
        original = self.case.evaluate(self.drafts, self.runs)
        bids = deepcopy(self.case.context["bids"])
        bids[-1]["alpha_usd_mt"] = "100.1234567890123456789"
        self.case.apply_tender(bids, self.case.context["evaluation_cutoff"])
        updated = self.case.evaluate(self.drafts, self.runs)
        self.assertEqual(original["baseline"], updated["baseline"])
        self.assertEqual(original["commercial_financials"]["pilog"], updated["commercial_financials"]["pilog"])
        self.assertNotEqual(original["commercial_financials"]["bid_amounts"], updated["commercial_financials"]["bid_amounts"])

    def test_new_case_end_to_end_and_round_four(self):
        case = self.case.revise()
        case.prepare(self.drafts); case.fix_freight(self.drafts)
        bids = deepcopy(self.case.context["bids"])
        bids.append({**bids[-1], "bid_id": "R4-B3", "round": 4, "alpha_usd_mt": "50"})
        case.apply_tender(bids, case.context["evaluation_cutoff"])
        result = case.evaluate(self.drafts, self.runs)
        self.assertEqual(result["recommendation"]["action"], "GO")
        self.assertEqual(result["tender"]["candidate_bid_ids"], ["R4-B3"])
        self.assertEqual(result["pricing"]["rate_mode"], "fixed_simulation")

    def test_bad_numeric_input_generates_data_issue_not_crash_or_go(self):
        case = self.case.revise()
        case.prepare(self.drafts); case.fix_freight(self.drafts)
        bids = deepcopy(self.case.context["bids"])
        bids[-1]["alpha_usd_mt"] = "NaN"
        case.apply_tender(bids, case.context["evaluation_cutoff"])
        result = case.evaluate(self.drafts, self.runs)
        self.assertEqual(result["recommendation"]["action"], "NO_GO")
        self.assertIn("DATA_ISSUE", result["recommendation"]["reason_codes"])

    def test_negative_stress_does_not_reprice_or_veto_go(self):
        case = self.case
        case.apply_scenarios([{"scenario_id": "delay", "label": "Delay besar", "extra_port_days": "100", "fuel_price_increase_fraction": "0"}])
        result = case.evaluate(self.drafts, self.runs)
        self.assertEqual(result["recommendation"]["action"], "GO")
        self.assertIn("STRESS_LOSS_DISCLOSED_NOT_VETO", result["recommendation"]["reason_codes"])
        self.assertEqual(result["scenarios"][0]["economics"]["freight_usd_mt"], result["scenarios"][1]["economics"]["freight_usd_mt"])
