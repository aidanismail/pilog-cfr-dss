from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from pilog_cfr_dss.orchestration.pipeline import evaluate


class Iteration2IntegrationTests(unittest.TestCase):
    dataset = ROOT / "data" / "dataset_ready.csv"
    catalog = ROOT / "data" / "reference" / "variable_catalog.csv"
    manual = ROOT / "data" / "raw" / "iteration_02_pre_offer_simulation.json"

    def test_current_case_has_two_commercial_alternatives(self) -> None:
        report = evaluate(self.dataset, self.catalog, self.manual)
        self.assertEqual([item["sales_term"] for item in report["scenarios"]], ["FOB", "CFR"])
        self.assertEqual(report["gate_1"]["outcome"], "CFR_ELIGIBLE")
        self.assertEqual(report["gate_2"]["outcome"], "CFR_CANDIDATE_PENDING_HUMAN_REVIEW")

    def test_route_comes_from_selected_csv_not_port_rule(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "other_route.csv"
            with self.dataset.open("r", encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            rows[1]["Value"] = "Port Alpha"
            rows[2]["Value"] = "Port Beta"
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["No", "Variable", "Value"])
                writer.writeheader()
                writer.writerows(rows)
            report = evaluate(path, self.catalog, self.manual)
        self.assertEqual(report["route"], {"origin": "Port Alpha", "destination": "Port Beta"})
        self.assertNotEqual(report["quality"]["status"], "BLOCK")

    def test_missing_cost_boundary_holds_gate_2_not_gate_1(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "manual.json"
            manual = json.loads(self.manual.read_text(encoding="utf-8"))
            manual["economic_definitions"]["other_voyage_cost_scope"] = "unconfirmed"
            path.write_text(json.dumps(manual), encoding="utf-8")
            report = evaluate(self.dataset, self.catalog, path)
        self.assertEqual(report["gate_1"]["outcome"], "CFR_ELIGIBLE")
        self.assertEqual(report["gate_2"]["outcome"], "HOLD_DATA_OR_DEFINITION")
        self.assertIn("UNCONFIRMED_DEFINITION:other_voyage_cost_scope", report["scenario_economics"]["CFR-PILOG"]["reasons"])


if __name__ == "__main__":
    unittest.main()
