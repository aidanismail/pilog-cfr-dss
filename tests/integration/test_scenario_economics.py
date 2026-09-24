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


class ScenarioEconomicsTests(unittest.TestCase):
    dataset = ROOT / "data" / "dataset_ready.csv"
    catalog = ROOT / "data" / "reference" / "variable_catalog.csv"
    manual = ROOT / "data" / "raw" / "iteration_02_pre_offer_simulation.json"

    def _dataset_with(self, path: Path, changes: dict[str, str]) -> None:
        with self.dataset.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        for row in rows:
            if row["Variable"] in changes:
                row["Value"] = changes[row["Variable"]]
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["No", "Variable", "Value"])
            writer.writeheader()
            writer.writerows(rows)

    def test_owned_cost_excludes_hire_and_daily_assumption(self) -> None:
        base = evaluate(self.dataset, self.catalog, self.manual)["scenario_economics"]["CFR-PILOG"]
        with tempfile.TemporaryDirectory() as temporary:
            altered = Path(temporary) / "dataset.csv"
            self._dataset_with(altered, {
                "Hire rate (USD/day)": "900000",
                "Daily cost assumption (USD/day)": "800000",
            })
            other = evaluate(altered, self.catalog, self.manual)["scenario_economics"]["CFR-PILOG"]
        self.assertEqual(base["total_freight_cost_usd"], other["total_freight_cost_usd"])
        self.assertEqual(base["net_freight_contribution_usd"], other["net_freight_contribution_usd"])

    def test_other_voyage_cost_changes_contribution_once(self) -> None:
        base = evaluate(self.dataset, self.catalog, self.manual)["scenario_economics"]["CFR-PILOG"]
        with tempfile.TemporaryDirectory() as temporary:
            altered = Path(temporary) / "dataset.csv"
            self._dataset_with(altered, {"Other voyage costs total (USD)": "210000"})
            other = evaluate(altered, self.catalog, self.manual)["scenario_economics"]["CFR-PILOG"]
        self.assertEqual(
            Decimal(other["total_freight_cost_usd"]) - Decimal(base["total_freight_cost_usd"]),
            Decimal("10000"),
        )
        self.assertEqual(
            Decimal(base["net_freight_contribution_usd"]) - Decimal(other["net_freight_contribution_usd"]),
            Decimal("10000"),
        )

    def test_missing_index_blocks_quality_not_invents_zero(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            altered = Path(temporary) / "manual.json"
            payload = json.loads(self.manual.read_text(encoding="utf-8"))
            payload["pricing"]["index"].pop("value")
            altered.write_text(json.dumps(payload), encoding="utf-8")
            report = evaluate(self.dataset, self.catalog, altered)
        self.assertEqual(report["quality"]["status"], "BLOCK")
        self.assertIsNone(report["pricing"]["fob_usd_mt"])
        self.assertEqual(report["gate_1"]["outcome"], "HOLD_DATA_ISSUE")


if __name__ == "__main__":
    unittest.main()
