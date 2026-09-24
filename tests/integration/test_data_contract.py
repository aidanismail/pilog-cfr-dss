"""Input-contract failures must fail closed before commercial selection."""

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
from pilog_cfr_dss.validation.ingest import load_snapshot


DATASET = ROOT / "data" / "dataset_ready.csv"
CATALOG = ROOT / "data" / "reference" / "variable_catalog.csv"
MANUAL = ROOT / "data" / "raw" / "iteration_02_pre_offer_simulation.json"


class DataContractTests(unittest.TestCase):
    def test_catalog_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            altered = Path(temporary) / "dataset.csv"
            with DATASET.open(encoding="utf-8-sig", newline="") as source:
                rows = list(csv.DictReader(source))
            rows[0]["Variable"] = "Unexpected variable"
            with altered.open("w", encoding="utf-8", newline="") as target:
                writer = csv.DictWriter(target, fieldnames=["No", "Variable", "Value"])
                writer.writeheader()
                writer.writerows(rows)
            with self.assertRaisesRegex(ValueError, "CATALOG_SOURCE_MISMATCH"):
                load_snapshot(altered, CATALOG, MANUAL)

    def test_manual_price_unit_mismatch_blocks_gate_1(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            altered = Path(temporary) / "manual.json"
            payload = json.loads(MANUAL.read_text(encoding="utf-8"))
            payload["pricing"]["index"]["unit"] = "USD/day"
            altered.write_text(json.dumps(payload), encoding="utf-8")
            report = evaluate(DATASET, CATALOG, altered)
            self.assertEqual(report["quality"]["status"], "BLOCK")
            self.assertEqual(report["gate_1"]["outcome"], "HOLD_DATA_ISSUE")
            self.assertIsNone(report["pricing"]["fob_usd_mt"])

    def test_obsolete_46k_allocation_input_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            altered = Path(temporary) / "dataset.csv"
            with DATASET.open(encoding="utf-8-sig", newline="") as source:
                rows = list(csv.DictReader(source))
            rows.insert(31, {"No": "32", "Variable": "Voyage expense allocation quantity (MT)", "Value": "46000"})
            with altered.open("w", encoding="utf-8", newline="") as target:
                writer = csv.DictWriter(target, fieldnames=["No", "Variable", "Value"])
                writer.writeheader()
                writer.writerows(rows)
            with self.assertRaisesRegex(ValueError, "OBSOLETE_ALLOCATION_QUANTITY"):
                load_snapshot(altered, CATALOG, MANUAL)


if __name__ == "__main__":
    unittest.main()
