from __future__ import annotations

import csv
import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from pilog_cfr_dss.orchestration.iteration_03 import evaluate, persist_run


ROOT = Path(__file__).resolve().parents[2]
GO = ROOT / "data" / "processed" / "i3_go_urea.json"
NO_GO = ROOT / "data" / "processed" / "i3_no_go_urea.json"
VOYAGE = ROOT / "data" / "processed" / "i3_urea_v1.csv"


class Iteration03IntegrationTests(unittest.TestCase):
    def make_case(self, folder: Path, fixture: dict | None = None, selling_rate: str | None = None,
                  overrides: dict[str, str] | None = None) -> Path:
        path = folder / "case.json"
        data = json.loads(GO.read_text(encoding="utf-8")) if fixture is None else fixture
        path.write_text(json.dumps(data), encoding="utf-8")
        with VOYAGE.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        if selling_rate is not None:
            next(row for row in rows if row["key"] == "freight_rate_usd_mt")["value"] = selling_rate
        for key, value in (overrides or {}).items():
            next(row for row in rows if row["key"] == key)["value"] = value
        with (folder / "i3_urea_v1.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        return path

    def test_two_presentation_cases_go_and_no_go(self) -> None:
        go, no_go = evaluate(GO), evaluate(NO_GO)
        self.assertEqual(go["recommendation"]["action"], "GO")
        self.assertEqual(no_go["recommendation"]["action"], "NO_GO")
        self.assertEqual(go["gates"]["gate_a"], "PASS")
        self.assertEqual(go["gates"]["gate_b"], "PASS")
        self.assertEqual(no_go["gates"]["gate_a"], "FAIL")
        self.assertEqual(no_go["gates"]["gate_b"], "NOT_EVALUATED")
        self.assertEqual(go["tender"]["index"]["index_usd_mt"], "410")
        self.assertEqual(go["tender"]["bids"][1]["fob_usd_mt"], "420")
        self.assertEqual(go["economics"]["pilog_freight_revenue_usd"], "900000")
        self.assertEqual(go["economics"]["commission_usd"], "56250.0000")
        self.assertEqual(go["economics"]["pilog_freight_contribution_usd"], "108446.1035119047619047619049")
        self.assertEqual(go["gates"]["selected_vessel_class"], "Supramax")
        self.assertEqual(len(go["input_lineage"]["voyage_fields"]), 29)
        self.assertTrue(all(item["source_status"].startswith("simulation_only")
                            for item in go["input_lineage"]["non_dataset_fields"]["bids"]))

    def test_equal_oe_floor_and_negative_alpha_can_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            fixture = json.loads(GO.read_text(encoding="utf-8"))
            fixture["bids"][1]["alpha_usd_mt"] = "5"
            report = evaluate(self.make_case(folder, fixture))
            self.assertEqual(report["recommendation"]["action"], "GO")
            self.assertEqual(report["selected_bid"]["oe_gap_usd_mt"], "0")
            fixture["oe_hps"]["value"] = "390"
            fixture["bids"][1]["alpha_usd_mt"] = "-10"
            report = evaluate(self.make_case(folder, fixture))
            self.assertEqual(report["recommendation"]["action"], "GO")
            self.assertEqual(report["selected_bid"]["alpha_usd_mt"], "-10")

    def test_positive_alpha_can_fail_floor(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = json.loads(GO.read_text(encoding="utf-8"))
            fixture["oe_hps"]["value"] = "430"
            report = evaluate(self.make_case(Path(directory), fixture))
            self.assertEqual(report["recommendation"]["action"], "NO_GO")
            self.assertEqual(report["recommendation"]["reason_category"], "TENDER_PRICE_FLOOR")

    def test_negative_contribution_fails_gate_b(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = evaluate(self.make_case(Path(directory), selling_rate="15"))
            self.assertEqual(report["gates"]["gate_a"], "PASS")
            self.assertEqual(report["gates"]["gate_b"], "FAIL")
            self.assertEqual(report["recommendation"]["action"], "NO_GO")
            self.assertIn("NEGATIVE_PILOG_FREIGHT_CONTRIBUTION", report["recommendation"]["reason_codes"])

    def test_no_vessel_class_passes_when_case_dwt_is_handysize_but_cargo_45k(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = evaluate(self.make_case(Path(directory), overrides={"dwt_mt": "35000"}))
            self.assertEqual(report["gates"]["gate_a"], "PASS")
            self.assertEqual(report["gates"]["gate_b"], "FAIL")
            self.assertIn("NO_VESSEL_CLASS_PASSED_DWT_SCREEN", report["recommendation"]["reason_codes"])
            self.assertIn("CARGO_EXCEEDS_DWT_AFTER_ALLOWANCES", report["recommendation"]["reason_codes"])

    def test_missing_numeric_voyage_value_is_no_go_data_issue(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = evaluate(self.make_case(Path(directory), overrides={"laden_distance_nm": ""}))
            self.assertEqual(report["recommendation"]["action"], "NO_GO")
            self.assertEqual(report["recommendation"]["reason_category"], "DATA_ISSUE")
            self.assertIn("MISSING_VALUE:laden_distance_nm", report["recommendation"]["reason_codes"][0])

    def test_missing_or_mismatched_index_is_no_go_data_issue_not_buyer_rejection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = json.loads(GO.read_text(encoding="utf-8"))
            del fixture["market_index"]["argus"]
            report = evaluate(self.make_case(Path(directory), fixture))
            self.assertEqual(report["recommendation"]["action"], "NO_GO")
            self.assertEqual(report["recommendation"]["reason_category"], "DATA_ISSUE")
            fixture = json.loads(GO.read_text(encoding="utf-8"))
            fixture["market_index"]["argus"]["basis"] = "CFR SEA granular"
            report = evaluate(self.make_case(Path(directory), fixture))
            self.assertEqual(report["recommendation"]["reason_category"], "DATA_ISSUE")

    def test_different_market_dates_or_unlabelled_oe_are_no_go_data_issue(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            fixture = json.loads(GO.read_text(encoding="utf-8"))
            fixture["market_index"]["argus"]["observation_date"] = "2026-10-01"
            report = evaluate(self.make_case(folder, fixture))
            self.assertEqual(report["recommendation"]["action"], "NO_GO")
            self.assertIn("INDEX_DATE_MISMATCH", report["recommendation"]["reason_codes"][0])
            fixture = json.loads(GO.read_text(encoding="utf-8"))
            del fixture["oe_hps"]["source_status"]
            report = evaluate(self.make_case(folder, fixture))
            self.assertEqual(report["recommendation"]["reason_category"], "DATA_ISSUE")
            self.assertIn("MISSING_SIMULATION_LABEL", report["recommendation"]["reason_codes"][0])

    def test_inherited_active_inputs_match_i2_source(self) -> None:
        with (ROOT / "data" / "processed" / "dataset_ready.csv").open(encoding="utf-8-sig", newline="") as handle:
            source_rows = list(csv.DictReader(handle))
        with (ROOT / "data" / "processed" / "variable_catalog.csv").open(encoding="utf-8-sig", newline="") as handle:
            catalog = list(csv.DictReader(handle))
        source = {spec["canonical_key"]: row["Value"] for row, spec in zip(source_rows, catalog, strict=True)}
        with VOYAGE.open(encoding="utf-8", newline="") as handle:
            active = list(csv.DictReader(handle))
        self.assertEqual(len(active), 29)
        for row in active:
            if row["source_status"] == "inherited_experimental":
                self.assertEqual(row["value"], source[row["key"]], row["key"])

    def test_input_snapshot_and_brief(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = persist_run(evaluate(GO), GO, Path(directory))
            saved = json.loads((run_dir / "decision_brief.json").read_text(encoding="utf-8"))
            brief = (run_dir / "decision_brief.md").read_text(encoding="utf-8")
            self.assertEqual(saved["recommendation"]["action"], "GO")
            self.assertEqual(set(saved["input_snapshot"]), {"case_fixture", "voyage_dataset", "vessel_policy"})
            self.assertIn("OE/HPS PI **sintetis**", brief)
            self.assertIn("bukan OD cost matrix resmi", brief)


if __name__ == "__main__":
    unittest.main()
