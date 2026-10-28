from copy import deepcopy
from decimal import Decimal as D, ROUND_CEILING, localcontext
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from pilog_cfr_dss.application.market_case import new_market_case, seed_demo_bids, apply_case_basis
from pilog_cfr_dss.application.interactive_case import InteractiveCase
from pilog_cfr_dss.sources.fearnpulse import latest_saved
from pilog_cfr_dss.validation.case_basis import COMMISSION_KEYS
from pilog_cfr_dss.orchestration.iteration_04 import evaluate
from pilog_cfr_dss.reporting.iteration_04 import commercial_brief, calculation_audit

class CaseBasisRevisionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.drafts, self.runs = Path(self.temp.name) / "drafts", Path(self.temp.name) / "runs"
        self.case = new_market_case(ROOT, latest_saved(ROOT))

    def finish(self):
        self.case.prepare(self.drafts); self.case.fix_freight(self.drafts)
        seed_demo_bids(self.case, ROOT)
        return self.case.evaluate(self.drafts, self.runs)

    def test_all_commissions_zero_and_pricing_independently_reconciles(self):
        self.assertTrue(all(self.case.values()[k] == "0" for k in COMMISSION_KEYS))
        result = self.finish(); base = result["baseline"]
        with localcontext() as precision:
            precision.prec = 40
            expected = ((D(base["voyage_expenses_usd"]) + D(result["pricing"]["basis"]["target_tce"]["value"]) * D(base["total_days"])) / D(result["case"]["cargo_mt"])).quantize(D("0.0001"), rounding=ROUND_CEILING)
            self.assertEqual(D(result["pricing"]["freight_tender_usd_mt"]), expected)
            self.assertEqual(D(base["commission_usd"]), 0)
            self.assertEqual(D(base["contribution_usd"]), D(base["revenue_usd"]) - D(base["total_cash_cost_usd"]))

    def test_od_only_distance_no_freight_reference_in_active_report(self):
        result = self.finish()
        self.assertNotIn("od_comparison", result)
        self.assertNotIn("od_reference", result["input_lineage"]["context"])
        self.assertEqual(result["route_distance"]["value"], "3906")
        self.assertEqual(result["route_distance"]["cell"], "H11")
        text = commercial_brief(result)
        self.assertIn("OD digunakan hanya untuk jarak", text)
        self.assertNotIn("versus OD", text)
        self.assertNotIn("Tarif OD", calculation_audit(result))
        self.assertIn("Komisi 0,00%", text)
        self.assertTrue((self.case.run_dir / "input_snapshot/od_distance.json").is_file())

    def test_nonzero_commission_cannot_sneak_into_policy_case(self):
        next(row for row in self.case.rows if row["key"] == "broker_fraction")["value"] = "0.01"
        result = evaluate(self.case.save(self.drafts))
        self.assertIn("ACTIVE_CASE_COMMISSION_MUST_BE_ZERO", result["recommendation"]["reason_codes"])

    def test_manual_changes_to_bound_distance_or_commission_are_atomic_rejections(self):
        original = self.case.fingerprint
        for edits in ({"distance_nm": "3907"}, {"freight_commission_fraction": "0.1"}):
            with self.subTest(edits=edits), self.assertRaises(ValueError):
                self.case.apply_inputs(edits, target_tce="14500", observations={}, oe_hps="420")
            self.assertEqual(self.case.fingerprint, original)

    def test_tampered_distance_is_not_reported_as_workbook_evidence(self):
        next(row for row in self.case.rows if row["key"] == "distance_nm")["value"] = "999"
        result = evaluate(self.case.save(self.drafts))
        self.assertIn("OD_DISTANCE_SOURCE_BINDING_MISMATCH", result["recommendation"]["reason_codes"])

    def test_raw_distance_payload_tampering_rejected(self):
        self.case.context["distance_reference"]["raw_payload"]["cells"]["H11"] = 999
        result = evaluate(self.case.save(self.drafts))
        self.assertIn("OD_DISTANCE_PAYLOAD_HASH_MISMATCH", result["recommendation"]["reason_codes"])

    def test_route_mismatch_rejected(self):
        next(row for row in self.case.rows if row["key"] == "discharging_port")["value"] = "Davao"
        result = evaluate(self.case.save(self.drafts))
        self.assertIn("OD_DISTANCE_SOURCE_BINDING_MISMATCH", result["recommendation"]["reason_codes"])

    def test_preview_prices_and_states_equal_final_engine_for_all_rounds(self):
        result = self.finish()
        preview = self.case.tender_preview()
        self.assertEqual(preview, result["tender"]["bids"])
        self.assertEqual({row["round"] for row in preview}, {1, 2, 3})
        self.assertEqual(len(preview), 9)
        for row in preview:
            self.assertEqual(D(row["fob_usd_mt"]), D(result["index"]["index_usd_mt"]) + D(row["alpha_usd_mt"]))
            self.assertEqual(D(row["cfr_usd_mt"]), D(row["fob_usd_mt"]) + D(row["freight_usd_mt"]))
        self.assertEqual(sum(row["is_latest"] for row in preview), 3)

    def test_policy_not_silently_applied_to_fixed_legacy_case(self):
        legacy = InteractiveCase.read(ROOT / "data/processed/i4_context.json")
        old = deepcopy(legacy.context["freight_tender"])
        with self.assertRaisesRegex(ValueError, "BASIS_FIXED"):
            apply_case_basis(legacy, ROOT)
        revised = legacy.revise(); apply_case_basis(revised, ROOT)
        self.assertFalse(revised.fixed)
        self.assertEqual(revised.context["bids"], [])
        self.assertEqual(old, legacy.context["freight_tender"])
        self.assertNotEqual(legacy.values()["broker_fraction"], "0")
