"""A persisted run must retain the precise input bytes it evaluated."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from pilog_cfr_dss.orchestration.pipeline import evaluate, persist_run


class RunSnapshotTests(unittest.TestCase):
    def test_run_contains_verified_input_snapshot(self) -> None:
        inputs = {
            "dataset": ROOT / "data" / "dataset_ready.csv",
            "catalog": ROOT / "data" / "reference" / "variable_catalog.csv",
            "manual": ROOT / "data" / "raw" / "iteration_02_pre_offer_simulation.json",
            "vessel_policy": ROOT / "data" / "reference" / "vessel_classes.json",
        }
        report = evaluate(inputs["dataset"], inputs["catalog"], inputs["manual"], inputs["vessel_policy"])
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = persist_run(report, Path(temporary), inputs)
            saved = json.loads((run_dir / "decision_brief.json").read_text(encoding="utf-8"))
            for label, metadata in saved["input_snapshot"].items():
                copied = run_dir / metadata["file"]
                self.assertTrue(copied.is_file())
                self.assertEqual(hashlib.sha256(copied.read_bytes()).hexdigest(), metadata["sha256"])
                self.assertEqual(metadata["sha256"], saved[f"{label}_sha256"])
            brief = (run_dir / "decision_brief.md").read_text(encoding="utf-8")
            self.assertIn("input_snapshot/dataset.csv", brief)


if __name__ == "__main__":
    unittest.main()
