from __future__ import annotations

import sys
import unittest
from decimal import Decimal as D
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from pilog_cfr_dss.decisions.gates import gate_1, gate_2
from pilog_cfr_dss.models.contracts import QualityResult, ScenarioEvidence


class GateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.context = {
            "mode": "simulation", "decision_stage": "pre_offer",
            "buyer_response": "not_approached",
            "commodity_seller": "PI Group entity", "freight_provider": "PILOG",
        }
        self.fob = ScenarioEvidence(
            "FOB-BASELINE", "FOB", None, None, True, None, None,
            "PRICE_BASELINE_ONLY", ("FOB_PRICE_AVAILABLE_NOT_PROFIT",),
        )

    def test_critical_quality_block_stops_gate_1(self) -> None:
        result = gate_1(QualityResult("BLOCK"), self.context)
        self.assertEqual(result["outcome"], "HOLD_DATA_ISSUE")

    def test_uncontacted_buyer_passes_but_declined_buyer_does_not(self) -> None:
        self.assertEqual(gate_1(QualityResult("WARN"), self.context)["outcome"], "CFR_ELIGIBLE")
        self.context["buyer_response"] = "declined_cfr"
        self.assertEqual(gate_1(QualityResult("WARN"), self.context)["outcome"], "CFR_OUT_OF_SCOPE")

    def test_positive_contribution_is_candidate_not_approval(self) -> None:
        cfr = ScenarioEvidence("CFR-PILOG", "CFR", "Supramax", "PILOG", True, True, D("100"), "CALCULATED")
        result = gate_2(
            gate_1(QualityResult("WARN"), self.context),
            (self.fob, cfr), "net_freight_contribution_usd", ("simulation only",),
        )
        self.assertEqual(result["outcome"], "CFR_CANDIDATE_PENDING_HUMAN_REVIEW")
        self.assertEqual(result["selected_scenario_id"], "CFR-PILOG")
        self.assertEqual(len(result["scenario_results"]), 2)

    def test_nonpositive_contribution_does_not_auto_recommend_fob(self) -> None:
        cfr = ScenarioEvidence("CFR-PILOG", "CFR", "Supramax", "PILOG", True, True, D("0"), "CALCULATED")
        result = gate_2(
            gate_1(QualityResult("WARN"), self.context),
            (self.fob, cfr), "net_freight_contribution_usd",
        )
        self.assertEqual(result["outcome"], "DEFER_FOB_REVIEW")
        self.assertIsNone(result["selected_scenario_id"])
        self.assertIn("FOB_ECONOMICS_NOT_AVAILABLE", result["reason_codes"])

    def test_missing_economics_holds(self) -> None:
        cfr = ScenarioEvidence("CFR-PILOG", "CFR", "Supramax", "PILOG", True, None, None, "HOLD_DEFINITION_REQUIRED")
        result = gate_2(
            gate_1(QualityResult("WARN"), self.context),
            (self.fob, cfr), "net_freight_contribution_usd",
        )
        self.assertEqual(result["outcome"], "HOLD_DATA_OR_DEFINITION")


if __name__ == "__main__":
    unittest.main()
