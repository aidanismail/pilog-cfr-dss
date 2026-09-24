"""Pre-offer, single-cargo, owned-vessel end-to-end simulation."""

from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from pilog_cfr_dss.orchestration.pipeline import evaluate


class OwnedEndToEndTests(unittest.TestCase):
    dataset = ROOT / "data" / "dataset_ready.csv"
    catalog = ROOT / "data" / "reference" / "variable_catalog.csv"
    manual = ROOT / "data" / "raw" / "iteration_02_pre_offer_simulation.json"

    def _alter_dataset(self, path: Path, label: str, value: str) -> None:
        with self.dataset.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        next(row for row in rows if row["Variable"] == label)["Value"] = value
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["No", "Variable", "Value"])
            writer.writeheader()
            writer.writerows(rows)

    def test_positive_pre_offer_case_reaches_both_gates_with_45k_basis(self) -> None:
        report = evaluate(self.dataset, self.catalog, self.manual)
        self.assertEqual(report["gate_1"]["outcome"], "CFR_ELIGIBLE")
        self.assertEqual(report["gate_2"]["outcome"], "CFR_CANDIDATE_PENDING_HUMAN_REVIEW")
        self.assertEqual(report["buyer_response"], "not_approached")
        self.assertEqual(report["quantity_basis"]["cargo_mt"], "45000")
        self.assertEqual(len(report["scenarios"]), 2)
        self.assertFalse(report["vessel_class_screen"]["Handysize"]["screen_pass"])
        self.assertTrue(report["vessel_class_screen"]["Supramax"]["screen_pass"])
        self.assertEqual(report["vessel_class_selection"]["selected_class"], "Supramax")
        self.assertEqual(Decimal(report["calculation_trace"]["results"]["loading_days"]["value"]), Decimal("4.5"))
        self.assertEqual(Decimal(report["calculation_trace"]["results"]["discharge_days"]["value"]), Decimal("7.5"))
        detail = report["scenario_economics"]["CFR-PILOG"]
        self.assertEqual(Decimal(detail["gross_freight_revenue_usd"]), Decimal("900000"))
        self.assertEqual(Decimal(detail["commission_usd"]), Decimal("56250"))
        self.assertEqual(Decimal(detail["cfr_usd_mt"]), Decimal("273"))
        self.assertEqual(
            Decimal(detail["net_freight_contribution_usd"]),
            Decimal(detail["gross_freight_revenue_usd"])
            - Decimal(detail["commission_usd"])
            - Decimal(detail["total_freight_cost_usd"]),
        )
        self.assertTrue(report["recommendation"]["human_approval_required"])

    def test_cargo_change_updates_port_days_revenue_and_commission(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            altered = Path(temporary) / "dataset.csv"
            self._alter_dataset(altered, "DWCC / cargo quantity (MT)", "40000")
            report = evaluate(altered, self.catalog, self.manual)
        detail = report["scenario_economics"]["CFR-PILOG"]
        self.assertEqual(Decimal(report["calculation_trace"]["results"]["loading_days"]["value"]), Decimal("4"))
        self.assertEqual(Decimal(detail["gross_freight_revenue_usd"]), Decimal("800000"))
        self.assertEqual(Decimal(detail["commission_usd"]), Decimal("50000"))
        self.assertEqual(detail["cargo_mt"], "40000")

    def test_nonpositive_contribution_defers_fob_economic_review(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            altered = Path(temporary) / "dataset.csv"
            self._alter_dataset(altered, "Freight rate (USD/MT)", "1")
            report = evaluate(altered, self.catalog, self.manual)
        self.assertEqual(report["gate_1"]["outcome"], "CFR_ELIGIBLE")
        self.assertEqual(report["gate_2"]["outcome"], "DEFER_FOB_REVIEW")
        self.assertEqual(report["pricing"]["fob_commodity_profit_status"], "NOT_ASSESSED")
        self.assertIsNone(report["gate_2"]["selected_scenario_id"])

    def test_buyer_declined_cfr_is_not_an_auto_fob_profit_claim(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            altered = Path(temporary) / "manual.json"
            payload = json.loads(self.manual.read_text(encoding="utf-8"))
            payload["buyer_response"] = "declined_cfr"
            altered.write_text(json.dumps(payload), encoding="utf-8")
            report = evaluate(self.dataset, self.catalog, altered)
        self.assertEqual(report["gate_1"]["outcome"], "CFR_OUT_OF_SCOPE")
        self.assertEqual(report["gate_2"]["outcome"], "DEFER_FOB_REVIEW")
        self.assertEqual(report["scenario_economics"], {})

    def test_cargo_exceeding_all_classes_defers(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            altered = Path(temporary) / "dataset.csv"
            self._alter_dataset(altered, "DWCC / cargo quantity (MT)", "61000")
            report = evaluate(altered, self.catalog, self.manual)
        self.assertEqual(report["gate_2"]["outcome"], "DEFER_FOB_REVIEW")
        self.assertIsNone(report["vessel_class_selection"]["preliminary_candidate_class"])


if __name__ == "__main__":
    unittest.main()
