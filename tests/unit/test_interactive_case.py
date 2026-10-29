import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from zipfile import ZipFile
from io import BytesIO

from pilog_cfr_dss.application.interactive_case import InteractiveCase
from pilog_cfr_dss.orchestration.iteration_04 import evaluate, prepare_voyage

ROOT = Path(__file__).resolve().parents[2]
GO = ROOT / "data/processed/i4_context.json"
NO = ROOT / "data/processed/i4_no_go.json"


class InteractiveCaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name)
        self.drafts = self.output / "ui_cases"
        self.runs = self.output / "runs"
        self.case = InteractiveCase.read(GO)

    def test_preparation_without_market_tender_scenarios_or_fake_bid(self):
        case = self.case.revise()
        for key in ("market_index", "oe_hps", "bids", "evaluation_cutoff", "scenarios", "vessel_policy"):
            case.context.pop(key, None)
        result = case.prepare(self.drafts)
        self.assertNotIn("recommendation", result)
        self.assertNotIn("tender", result)
        self.assertEqual(result["baseline"], evaluate(GO)["baseline"])
        self.assertNotIn("bids", case.context)
        final = evaluate(case.save(self.drafts))
        self.assertEqual(final["recommendation"]["action"], "NO_GO")
        self.assertIn("DATA_ISSUE", final["recommendation"]["reason_codes"])

    def test_final_validator_still_requires_nonempty_bids(self):
        case = self.case.revise()
        case.prepare(self.drafts); case.fix_freight(self.drafts)
        result = case.evaluate(self.drafts, self.runs)
        self.assertIn("MISSING_BIDS", result["recommendation"]["reason_codes"])
        self.assertEqual(result["recommendation"]["gate_a"], "NOT_EVALUATED")

    def test_preparation_invalid_critical_input_does_not_default_to_zero(self):
        case = self.case.revise()
        next(row for row in case.rows if row["key"] == "speed_knots")["value"] = "0"
        with self.assertRaisesRegex(ValueError, "NONPOSITIVE_INPUT:speed_knots"):
            case.prepare(self.drafts)
        self.assertIsNone(case.preparation)
        self.assertIsNone(case.result)

    def test_cannot_evaluate_or_fix_before_ready(self):
        case = self.case.revise()
        with self.assertRaisesRegex(ValueError, "FREIGHT_NOT_FIXED"):
            case.evaluate(self.drafts, self.runs)
        with self.assertRaisesRegex(ValueError, "CALCULATE_VOYAGE_FIRST"):
            case.fix_freight(self.drafts)

    def test_save_is_reusable_and_reopen_keeps_exact_case(self):
        path = self.case.save(self.drafts)
        self.assertEqual(path, self.case.save(self.drafts))
        reopened = InteractiveCase.reopen(path, self.drafts)
        self.assertEqual(reopened.context, self.case.context)
        self.assertEqual(reopened.rows, self.case.rows)
        self.assertEqual(reopened.fingerprint, self.case.fingerprint)

    def test_reopen_and_dataset_paths_cannot_escape_workspace(self):
        with self.assertRaisesRegex(ValueError, "DRAFT_OUTSIDE"):
            InteractiveCase.reopen(GO, self.drafts)
        self.case.context["voyage_dataset"] = "../private.csv"
        with self.assertRaisesRegex(ValueError, "INVALID_DATASET_PATH"):
            self.case.save(self.drafts)

    def test_revise_drops_bids_selection_fixed_and_result(self):
        self.case.context["pi_selected_bid_id"] = "R3-B1"
        revised = self.case.revise()
        self.assertFalse(revised.fixed)
        self.assertEqual(revised.context["bids"], [])
        self.assertNotIn("pi_selected_bid_id", revised.context)
        self.assertEqual(revised.rows, self.case.rows)
        self.assertNotEqual(revised.draft_id, self.case.draft_id)
        revised.rows[0]["value"] = "changed"
        self.assertNotEqual(revised.rows[0], self.case.rows[0])

    def test_fixed_basis_cannot_silently_reprice(self):
        self.case.prepare(self.drafts)
        fixed = deepcopy(self.case.context["freight_tender"])
        with self.assertRaisesRegex(ValueError, "BASIS_FIXED_CREATE_REVISION"):
            self.case.apply_inputs({"cargo_mt": "45000"}, target_tce="1", observations={}, oe_hps="420")
        self.case.fix_freight(self.drafts)
        self.assertEqual(fixed, self.case.context["freight_tender"])

    def test_explicit_fix_uses_shared_pricing_and_freezes(self):
        case = self.case.revise()
        prepared = case.prepare(self.drafts)
        self.assertEqual(case.state, "VOYAGE_CALCULATED")
        case.fix_freight(self.drafts)
        self.assertEqual(case.state, "FREIGHT_FIXED")
        self.assertEqual(case.context["freight_tender"]["value"], prepared["pricing"]["computed_freight_usd_mt"])
        self.assertEqual(case.context["freight_tender"]["voyage_dataset_sha256"],
                         {k: v for k, v in prepared["input_hashes"].items() if k.endswith(".csv")})

    def test_edit_numeric_string_preserves_precision_lineage_and_invalidates(self):
        case = self.case.revise(); case.prepare(self.drafts)
        rate = "701.123456789012345678901234567890"
        case.apply_inputs({"do_price_usd_mt": rate}, target_tce="13000", observations={}, oe_hps="420")
        self.assertIsNone(case.preparation)
        row = next(r for r in case.rows if r["key"] == "do_price_usd_mt")
        self.assertEqual(row["value"], rate)
        self.assertEqual(row["source_status"], "simulation_only_user_input")
        self.assertIn("sumber awal", row["note"])

    def test_bid_round_requires_integer_without_silent_truncation(self):
        bid = {**self.case.context["bids"][0], "round": "1.5"}
        before = self.case.fingerprint
        with self.assertRaisesRegex(ValueError, "bilangan bulat"):
            self.case.apply_tender([bid], self.case.context["evaluation_cutoff"])
        self.assertEqual(before, self.case.fingerprint)

    def test_changed_market_value_no_longer_claims_original_pdf_hash(self):
        case = self.case.revise()
        original_hash = case.context["market_index"]["argus"]["sha256"]
        case.apply_inputs({}, target_tce="13000", observations={"argus": {"low": "418"}}, oe_hps="420")
        record = case.context["market_index"]["argus"]
        self.assertNotIn("sha256", record)
        self.assertEqual(record["prior_source"]["sha256"], original_hash)
        self.assertEqual(record["source_status"], "simulation_only_user_input")

    def test_preparation_od_mismatch_is_not_a_gate(self):
        case = self.case.revise()
        next(r for r in case.rows if r["key"] == "cargo_mt")["value"] = "29000"
        report = case.prepare(self.drafts)
        self.assertIsNone(report["od_comparison"]["rate_usd_mt"])
        self.assertTrue(any("OD_CASE_BASIS_MISMATCH" in n for n in report["notes"]))

    def test_no_duplicate_run_on_rerender_and_download(self):
        result = self.case.evaluate(self.drafts, self.runs)
        self.assertEqual(result, self.case.evaluate(self.drafts, self.runs))
        self.assertEqual(len(list(self.runs.iterdir())), 1)
        with ZipFile(BytesIO(self.case.bundle())) as archive:
            names = archive.namelist()
            self.assertIn("commercial_decision_brief.md", names)
            self.assertIn("input_snapshot/case_fixture.json", names)
            saved = json.loads(archive.read("result.json"))
        self.assertEqual(saved["run_id"], result["run_id"])
        replay = evaluate(self.case.run_dir / "input_snapshot/case_fixture.json")
        self.assertEqual(replay["baseline"], result["baseline"])
        self.assertEqual(replay["recommendation"], result["recommendation"])

    def test_bid_edit_invalidates_old_result_and_download_but_not_fixed(self):
        self.case.evaluate(self.drafts, self.runs)
        fixed = deepcopy(self.case.context["freight_tender"])
        bids = deepcopy(self.case.context["bids"]); bids[-1]["alpha_usd_mt"] = "100"
        self.case.apply_tender(bids, self.case.context["evaluation_cutoff"])
        self.assertIsNone(self.case.result)
        self.assertIsNone(self.case.run_dir)
        self.assertEqual(fixed, self.case.context["freight_tender"])
        with self.assertRaisesRegex(ValueError, "NO_CURRENT_RESULT"):
            self.case.bundle()
        self.assertEqual(len(list(self.runs.iterdir())), 1)

    def test_blank_extra_bid_row_ignored_but_zero_alpha_kept(self):
        bid = {**self.case.context["bids"][0], "alpha_usd_mt": "0"}
        self.case.apply_tender([bid, {"bid_id": None, "alpha_usd_mt": ""}], self.case.context["evaluation_cutoff"])
        self.assertEqual(len(self.case.context["bids"]), 1)
        self.assertEqual(self.case.context["bids"][0]["alpha_usd_mt"], "0")
