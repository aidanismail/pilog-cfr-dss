import csv
import hashlib
import json
import tempfile
import unittest
from copy import deepcopy
from decimal import Decimal as D
from pathlib import Path

from pilog_cfr_dss.orchestration.iteration_04 import evaluate, persist_run, fixed_freight_record
from pilog_cfr_dss.reporting.iteration_04 import commercial_brief, calculation_audit, amount
from pilog_cfr_dss.decisions.iteration_04 import decide
from pilog_cfr_dss.decisions.iteration_04 import evaluate_tender
from pilog_cfr_dss.calculations.tender_04 import index_prices, bid_prices
from pilog_cfr_dss.validation.iteration_04 import load_case

ROOT = Path(__file__).resolve().parents[2]
GO = ROOT / "data/processed/i4_context.json"
NO = ROOT / "data/processed/i4_no_go.json"
CSV = ROOT / "data/processed/i4_voyage.csv"


class I4IntegrationTests(unittest.TestCase):
    def make_case(self, folder, fixture=None, overrides=None):
        payload = deepcopy(fixture) if fixture is not None else json.loads(GO.read_text(encoding="utf-8"))
        path = folder / "case.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        with CSV.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        for key, value in (overrides or {}).items():
            row = next(r for r in rows if r["key"] == key)
            row.update(value if isinstance(value, dict) else {"value": value})
        with (folder / "i4_voyage.csv").open("w", encoding="utf-8", newline="") as stream:
            w = csv.DictWriter(stream, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
        return path

    def test_go_no_go_use_same_voyage_and_index_only_alpha_changes(self):
        a, b = evaluate(GO), evaluate(NO)
        self.assertEqual(a["recommendation"]["action"], "GO")
        self.assertEqual(b["recommendation"]["action"], "NO_GO")
        self.assertEqual(a["baseline"], b["baseline"])
        self.assertEqual(a["index"], b["index"])
        self.assertEqual(b["recommendation"]["gate_b"], "NOT_EVALUATED")
        self.assertEqual(b["recommendation"]["checks"][1]["status"], "Lolos")
        self.assertEqual(b["recommendation"]["checks"][2]["status"], "Tidak lolos")
        self.assertIn("hanya indikatif", commercial_brief(b))
        self.assertEqual(a["tender"]["candidate_bid_ids"], ["R3-B1"])
        self.assertEqual(a["index"]["index_usd_mt"], "415.00")
        self.assertEqual(a["baseline"]["freight_usd_mt"], "24.8957")
        self.assertEqual(D(a["baseline"]["contribution_usd"]), D("188856.76125"))
        self.assertEqual(a["input_hashes"][CSV.name], b["input_hashes"][CSV.name])

    def test_go_with_negative_stress_is_not_vetoed(self):
        r = evaluate(GO)
        self.assertIn("port_delay", r["recommendation"]["negative_stress_ids"])
        self.assertEqual(r["recommendation"]["action"], "GO")
        self.assertTrue(all(s["economics"]["freight_usd_mt"] == r["baseline"]["freight_usd_mt"] for s in r["scenarios"]))
        self.assertIn("Perubahan dari baseline USD", commercial_brief(r))
        self.assertIn("-239.020,80", commercial_brief(r))

    def test_dates_and_missing_asof_do_not_change_economics_or_go(self):
        payload = json.loads(GO.read_text(encoding="utf-8"))
        payload["market_index"]["argus"]["observation_date"] = "2020-01-01"
        payload["market_index"]["fertecon"].pop("observation_date")
        with tempfile.TemporaryDirectory() as t:
            r = evaluate(self.make_case(Path(t), payload))
            self.assertEqual(r["recommendation"]["action"], "GO")
            self.assertEqual(r["baseline"], evaluate(GO)["baseline"])
            self.assertIn("Tanggal dua laporan", " ".join(r["notes"]))

    def test_floor_equality_and_no_implicit_id_requirement(self):
        p = json.loads(GO.read_text(encoding="utf-8"))
        p["bids"] = [{**p["bids"][-1], "alpha_usd_mt": "5"}]
        with tempfile.TemporaryDirectory() as t:
            r = evaluate(self.make_case(Path(t), p))
            self.assertEqual(r["recommendation"]["gate_a"], "PASS")
            self.assertEqual(D(r["tender"]["bids"][0]["oe_gap_usd_mt"]), 0)
            self.assertEqual(r["tender"]["award_status"], "NOT_AWARDED_BY_SYSTEM")

    def test_positive_alpha_still_fails_high_floor(self):
        p = json.loads(GO.read_text(encoding="utf-8")); p["oe_hps"]["value"] = "1000"
        with tempfile.TemporaryDirectory() as t:
            r = evaluate(self.make_case(Path(t), p))
            self.assertEqual(r["recommendation"]["action"], "NO_GO")

    def test_withdrawn_latest_does_not_resurrect_old_bid(self):
        p = json.loads(GO.read_text(encoding="utf-8"))
        p["bids"] = [b for b in p["bids"] if b["buyer_id"] == "BUYER-1"]
        p["bids"][-1]["status"] = "withdrawn"
        with tempfile.TemporaryDirectory() as t:
            r = evaluate(self.make_case(Path(t), p))
            self.assertEqual(r["tender"]["ranking"], [])
            self.assertFalse(any(b["is_active_at_cutoff"] for b in r["tender"]["bids"]))

    def test_round_four_and_ties_not_auto_awarded(self):
        p = json.loads(GO.read_text(encoding="utf-8"))
        for i in (1, 2):
            p["bids"].append({"bid_id": f"R4-B{i}", "buyer_id": f"BUYER-{i}", "round": 4, "sequence": i,
                              "alpha_usd_mt": "20", "status": "active", "source_status": "simulation_only_synthetic"})
        with tempfile.TemporaryDirectory() as t:
            r = evaluate(self.make_case(Path(t), p))
            self.assertEqual(r["tender"]["top_tied_bid_ids"], ["R4-B1", "R4-B2"])
            self.assertEqual(r["recommendation"]["action"], "GO")

    def test_future_bid_not_current_and_expired_latest_not_resurrected(self):
        p = json.loads(GO.read_text(encoding="utf-8"))
        p["bids"] = [b for b in p["bids"] if b["buyer_id"] == "BUYER-1"]
        p["bids"][-1]["submitted_at"] = "2027-01-01T00:00:00+00:00"
        with tempfile.TemporaryDirectory() as t:
            path = self.make_case(Path(t), p)
            r = evaluate(path)
            self.assertTrue(next(b for b in r["tender"]["bids"] if b["round"] == 2)["is_active_at_cutoff"])
            p["bids"][-1]["submitted_at"] = "2026-09-10T00:00:00+00:00"
            p["bids"][-1]["valid_until"] = "2026-09-10T01:00:00+00:00"
            path.write_text(json.dumps(p), encoding="utf-8")
            self.assertEqual(evaluate(path)["tender"]["ranking"], [])

    def test_pi_selection_cannot_force_invalid_bid(self):
        p = json.loads(GO.read_text(encoding="utf-8")); p["pi_selected_bid_id"] = "R1-B1"
        with tempfile.TemporaryDirectory() as t:
            r = evaluate(self.make_case(Path(t), p))
            self.assertEqual(r["recommendation"]["action"], "NO_GO")
            self.assertIn("PI_SELECTION_NOT_ELIGIBLE", r["recommendation"]["reason_codes"])

    def test_baseline_negative_when_freight_fixed_does_not_reprice_to_go(self):
        p = json.loads(GO.read_text(encoding="utf-8"))
        p["freight_tender"] = {"value": "1", "unit": "USD/MT", "source_status": "simulation_only_test"}
        with tempfile.TemporaryDirectory() as t:
            r = evaluate(self.make_case(Path(t), p))
            self.assertEqual(r["recommendation"]["gate_a"], "PASS")
            self.assertEqual(r["recommendation"]["gate_b"], "FAIL")
            self.assertIn("NEGATIVE_BASELINE_CONTRIBUTION", r["recommendation"]["reason_codes"])

    def test_zero_baseline_contribution_is_accepted(self):
        case, _ = load_case(GO)
        r = evaluate(GO)
        index = index_prices(case.context["market_index"])["index_usd_mt"]
        typed_tender = evaluate_tender(bid_prices(index, D(case.context["oe_hps"]["value"]), D(r["baseline"]["freight_usd_mt"]), case.context["bids"]), case.context)
        rec = decide(case, typed_tender, {"contribution_usd": D(0)}, [])
        self.assertEqual(rec["action"], "GO")
        self.assertIn("BASELINE_BREAK_EVEN", rec["reason_codes"])

    def test_capacity_failure_not_hidden(self):
        with tempfile.TemporaryDirectory() as t:
            r = evaluate(self.make_case(Path(t), overrides={"dwt_mt": "25000"}))
            self.assertEqual(r["recommendation"]["action"], "NO_GO")
            self.assertIn("CARGO_EXCEEDS_CASE_GROSS_DWT", r["recommendation"]["reason_codes"])

    def test_critical_numeric_units_or_nonfinite_fail_with_brief(self):
        for change in ["", "NaN", "Infinity", "0", {"value": "100", "unit": "km"}]:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as t:
                r = evaluate(self.make_case(Path(t), overrides={"speed_knots": change}))
                self.assertEqual(r["recommendation"]["action"], "NO_GO")
                self.assertIn("DATA_ISSUE", r["recommendation"]["reason_codes"])
                self.assertIn("Perhitungan belum", commercial_brief(r))

    def test_od_tariff_is_unmodified_one_way_with_return_cost_not_a_gate(self):
        r = evaluate(GO)
        self.assertEqual(r["od_comparison"]["quote_basis"], "one_way_shipment")
        self.assertEqual(r["od_comparison"]["od_cost_coverage"], "includes_return")
        self.assertEqual(r["od_comparison"]["rate_usd_mt"], "29.184092855946123")
        p = json.loads(GO.read_text(encoding="utf-8")); p.pop("od_reference")
        with tempfile.TemporaryDirectory() as t:
            r = evaluate(self.make_case(Path(t), p))
            self.assertEqual(r["recommendation"]["action"], "GO")
            self.assertIsNone(r["od_comparison"]["rate_usd_mt"])

    def test_snapshot_uses_evaluated_bytes_even_if_live_input_changes(self):
        with tempfile.TemporaryDirectory() as t:
            folder = Path(t); path = self.make_case(folder); r = evaluate(path)
            path.write_text("{}", encoding="utf-8")
            output = persist_run(r, folder / "runs")
            for name, digest in r["input_hashes"].items():
                self.assertEqual(hashlib.sha256((output / "input_snapshot" / name).read_bytes()).hexdigest(), digest)
            replay = evaluate(output / "input_snapshot/case_fixture.json")
            self.assertEqual(replay["baseline"], r["baseline"])
            self.assertEqual(replay["recommendation"], r["recommendation"])
            self.assertIn("tarif od berlaku satu arah", (output / "commercial_decision_brief.md").read_text(encoding="utf-8").lower())

    def test_malformed_context_shapes_do_not_crash_or_default_to_go(self):
        for field, bad in [("bids", [None]), ("market_index", []), ("pricing", None), ("scenarios", [None]), ("oe_hps", "420")]:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as t:
                p = json.loads(GO.read_text(encoding="utf-8")); p[field] = bad
                r = evaluate(self.make_case(Path(t), p))
                self.assertEqual(r["recommendation"]["action"], "NO_GO")
                self.assertIn("DATA_ISSUE", r["recommendation"]["reason_codes"])

    def test_wrong_product_basis_is_not_just_mixed_date_warning(self):
        p = json.loads(GO.read_text(encoding="utf-8")); p["market_index"]["argus"]["basis"] = "CFR SEA granular"
        with tempfile.TemporaryDirectory() as t:
            r = evaluate(self.make_case(Path(t), p))
            self.assertEqual(r["recommendation"]["action"], "NO_GO")

    def test_e2e_exact_break_even_boundary_fixture(self):
        p = json.loads(GO.read_text(encoding="utf-8"))
        # This is an intentional new pricing example, not evaluation of a fixed offer.
        p.pop("freight_tender", None)
        p["pricing"]["target_tce"]["value"] = "100"
        changes = {"cargo_mt": "100", "distance_nm": "240", "speed_knots": "10",
                   "loading_rate_mt_day": "100", "discharge_rate_mt_day": "100",
                   "sea_fo_mt_day": "0", "sea_do_mt_day": "0", "port_do_mt_day": "0",
                   "running_usd_day": "100", "port_other_total_usd": "300",
                   "freight_commission_fraction": "0", "broker_fraction": "0", "additional_commission_fraction": "0"}
        with tempfile.TemporaryDirectory() as t:
            r = evaluate(self.make_case(Path(t), p, changes))
            self.assertEqual(D(r["baseline"]["total_days"]), D(3))
            self.assertEqual(D(r["baseline"]["freight_usd_mt"]), D(6))
            self.assertEqual(D(r["baseline"]["contribution_usd"]), D(0))
            self.assertEqual(r["recommendation"]["action"], "GO")
            self.assertIn("BASELINE_BREAK_EVEN", r["recommendation"]["reason_codes"])
            self.assertIn("REVIEW_ZERO_BUFFER", [s["code"] for s in r["recommendation"]["next_steps"]])
            self.assertEqual(D(r["metrics"]["additional_port_days_to_break_even"]), D(0))
            self.assertIn("baseline tepat impas", commercial_brief(r))

    def test_route_and_quantity_are_inputs_not_port_or_30k_lock(self):
        p = json.loads(GO.read_text(encoding="utf-8"))
        p.pop("freight_tender", None)  # New route/quantity offer is priced explicitly.
        with tempfile.TemporaryDirectory() as t:
            r = evaluate(self.make_case(Path(t), p, overrides={"discharging_port": "TEST-PORT", "cargo_mt": "20000"}))
            self.assertEqual(r["case"]["discharging_port"], "TEST-PORT")
            self.assertEqual(r["recommendation"]["action"], "GO")
            self.assertIsNone(r["od_comparison"]["rate_usd_mt"])
            self.assertEqual(D(r["baseline"]["loading_days"]), D(4))

    def test_duplicate_bid_and_impossible_commission_are_data_issues(self):
        p = json.loads(GO.read_text(encoding="utf-8")); p["bids"].append(deepcopy(p["bids"][0]))
        with tempfile.TemporaryDirectory() as t:
            r = evaluate(self.make_case(Path(t), p))
            self.assertIn("DATA_ISSUE", r["recommendation"]["reason_codes"])
        with tempfile.TemporaryDirectory() as t:
            r = evaluate(self.make_case(Path(t), overrides={"freight_commission_fraction": "1"}))
            self.assertIn("DATA_ISSUE", r["recommendation"]["reason_codes"])

    def test_duplicate_csv_key_does_not_silently_override(self):
        with tempfile.TemporaryDirectory() as t:
            path = self.make_case(Path(t))
            data = Path(t) / "i4_voyage.csv"
            with data.open(encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream))
            with data.open("w", encoding="utf-8", newline="") as stream:
                w = csv.DictWriter(stream, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows + [rows[0]])
            r = evaluate(path)
            self.assertIn("I4_DATASET_KEY_MISMATCH", r["recommendation"]["reason_codes"])

    def test_gross_quote_cannot_silently_be_used_as_net_tce(self):
        p = json.loads(GO.read_text(encoding="utf-8")); p["pricing"]["quote_commission_basis"] = "gross"
        with tempfile.TemporaryDirectory() as t:
            r = evaluate(self.make_case(Path(t), p))
            self.assertIn("QUOTE_COMMISSION_BASIS_REQUIRES_NORMALIZATION", r["recommendation"]["reason_codes"])

    def test_duplicate_json_key_is_not_silently_overwritten(self):
        with tempfile.TemporaryDirectory() as t:
            path = self.make_case(Path(t))
            content = path.read_text(encoding="utf-8")
            path.write_text(content.replace('"alpha_usd_mt": "12"', '"alpha_usd_mt": "12", "alpha_usd_mt": "999"'), encoding="utf-8")
            r = evaluate(path)
            self.assertEqual(r["recommendation"]["action"], "NO_GO")
            self.assertIn("DUPLICATE_JSON_KEY:alpha_usd_mt", r["recommendation"]["reason_codes"])


    def test_latest_table_and_all_bid_audit_show_same_visible_freight(self):
        for path in (GO, NO):
            r = evaluate(path)
            self.assertEqual(len(r["tender"]["latest_bids"]), 3)
            for bid in r["tender"]["bids"]:
                self.assertEqual(bid["freight_usd_mt"], r["baseline"]["freight_usd_mt"])
                self.assertEqual(D(bid["cfr_usd_mt"]), D(bid["fob_usd_mt"]) + D(bid["freight_usd_mt"]))
            brief, audit = commercial_brief(r), calculation_audit(r)
            latest_table = brief.split("| Peringkat", 1)[1].split("\n\n", 1)[0]
            rows = [line for line in latest_table.splitlines() if "BUYER-" in line]
            self.assertEqual(len(rows), 3)
            self.assertTrue(all(line.split("|")[5].strip() == "24,90" for line in rows))
            for bid in r["tender"]["latest_bids"]:
                self.assertIn(bid["bid_id"], latest_table)
            self.assertIn("Freight terlihat buyer", audit)
            for bid in r["tender"]["bids"]:
                self.assertIn("| " + bid["bid_id"] + " |", audit)

    def test_internal_classification_does_not_claim_buyer_can_see_floor(self):
        r = evaluate(GO)
        self.assertEqual(r["audience"], "INTERNAL_PI_PILOG")
        self.assertEqual(r["classification"], "INTERNAL_NOT_FOR_BUYERS")
        self.assertIn("bukan materi buyer", commercial_brief(r))
        self.assertIn("bukan untuk buyer", calculation_audit(r))
        self.assertIn("bukan CFR − OE/HPS", commercial_brief(r))
        self.assertIn("tidak untuk dibagikan kepada buyer", commercial_brief(r))

    def test_no_go_floor_has_best_active_identity_shortfall_and_floor_alpha(self):
        r = evaluate(NO)
        best = r["tender"]["best_active_bid"]
        self.assertEqual(best["bid_id"], "R3-B3")
        self.assertEqual(D(best["floor_shortfall_usd_mt"]), D(19))
        self.assertEqual(D(r["metrics"]["minimum_alpha_usd_mt"]), D(5))
        self.assertEqual(r["recommendation"]["gate_b"], "NOT_EVALUATED")
        self.assertIn("REVIEW_TENDER_FLOOR", [s["code"] for s in r["recommendation"]["next_steps"]])
        self.assertIn("19,00 USD/MT", commercial_brief(r))

    def test_no_active_bid_does_not_invent_best_bid_or_resurrect_old(self):
        p = json.loads(GO.read_text(encoding="utf-8"))
        for b in p["bids"]:
            if b["round"] == 3:
                b["status"] = "withdrawn"
        with tempfile.TemporaryDirectory() as t:
            r = evaluate(self.make_case(Path(t), p))
        self.assertIsNone(r["tender"]["best_active_bid"])
        self.assertEqual(len(r["tender"]["latest_bids"]), 3)
        self.assertFalse(any(b["eligible"] for b in r["tender"]["latest_bids"]))
        self.assertIn("REVIEW_BID_VALIDITY", [s["code"] for s in r["recommendation"]["next_steps"]])
        self.assertIn("best active bid dan shortfall tidak dapat", commercial_brief(r))

    def test_optional_pi_choice_may_be_eligible_without_being_top_ranked(self):
        p = json.loads(GO.read_text(encoding="utf-8")); p["pi_selected_bid_id"] = "R3-B2"
        with tempfile.TemporaryDirectory() as t:
            r = evaluate(self.make_case(Path(t), p))
        self.assertEqual(r["recommendation"]["action"], "GO")
        self.assertEqual(r["tender"]["candidate_bid_ids"], ["R3-B2"])
        self.assertEqual(r["tender"]["ranking"][0], "R3-B1")
        self.assertIn("pilihan PI", commercial_brief(r))
        self.assertEqual(r["tender"]["award_status"], "NOT_AWARDED_BY_SYSTEM")

    def test_tied_prices_share_rank_but_are_not_awarded(self):
        p = json.loads(GO.read_text(encoding="utf-8"))
        p["bids"][-2]["alpha_usd_mt"] = "12"
        with tempfile.TemporaryDirectory() as t:
            r = evaluate(self.make_case(Path(t), p))
        ranks = {b["bid_id"]: b["eligible_rank"] for b in r["tender"]["latest_bids"]}
        self.assertEqual(ranks, {"R3-B1": 1, "R3-B2": 1, "R3-B3": 3})
        self.assertIn("REVIEW_TIE", [s["code"] for s in r["recommendation"]["next_steps"]])
        self.assertIn("Peringkat tertinggi seri", commercial_brief(r))

    def test_default_fixed_rate_cost_and_target_changes_do_not_reprice(self):
        p = json.loads(GO.read_text(encoding="utf-8"))
        self.assertIn("freight_tender", p)
        p["pricing"]["target_tce"]["value"] = "99999"
        with tempfile.TemporaryDirectory() as t:
            r = evaluate(self.make_case(Path(t), p, {"port_other_total_usd": "1000000"}))
        self.assertEqual(r["pricing"]["rate_mode"], "fixed_simulation")
        self.assertEqual(r["baseline"]["freight_usd_mt"], evaluate(GO)["baseline"]["freight_usd_mt"])
        self.assertNotEqual(r["pricing"]["computed_freight_usd_mt"], r["baseline"]["freight_usd_mt"])
        self.assertEqual(r["recommendation"]["action"], "NO_GO")
        self.assertIn("REVIEW_BASELINE_COST", [s["code"] for s in r["recommendation"]["next_steps"]])
        self.assertIsNone(r["metrics"]["additional_port_days_to_break_even"])

    def test_legacy_input_without_fixed_price_is_honestly_labelled_indication(self):
        p = json.loads(GO.read_text(encoding="utf-8")); p.pop("freight_tender", None)
        with tempfile.TemporaryDirectory() as t:
            r = evaluate(self.make_case(Path(t), p))
        self.assertEqual(r["baseline"], evaluate(GO)["baseline"])
        self.assertEqual(r["pricing"]["rate_mode"], "model_indication")
        self.assertIn("belum disimpan sebagai harga tetap", commercial_brief(r))
        self.assertEqual(fixed_freight_record(r)["value"], r["baseline"]["freight_usd_mt"])

    def test_zero_daily_incremental_cost_reports_unknown_not_infinity(self):
        with tempfile.TemporaryDirectory() as t:
            r = evaluate(self.make_case(Path(t), overrides={"running_usd_day": "0", "port_do_mt_day": "0"}))
        self.assertEqual(r["recommendation"]["action"], "GO")
        self.assertIsNone(r["metrics"]["additional_port_days_to_break_even"])
        self.assertIn("biaya harian tambahan model nol", commercial_brief(r))

    def test_specific_actions_for_selection_capacity_and_data_failures(self):
        p = json.loads(GO.read_text(encoding="utf-8")); p["pi_selected_bid_id"] = "R1-B1"
        cases = [(p, {}, "REVIEW_PI_SELECTION"), (None, {"dwt_mt": "25000"}, "REVIEW_VESSEL_SCREEN"),
                 (None, {"speed_knots": "0"}, "CORRECT_CRITICAL_INPUT")]
        for fixture, changes, code in cases:
            with self.subTest(code=code), tempfile.TemporaryDirectory() as t:
                r = evaluate(self.make_case(Path(t), fixture, changes))
                self.assertEqual(r["recommendation"]["action"], "NO_GO")
                self.assertIn(code, [s["code"] for s in r["recommendation"]["next_steps"]])
                self.assertIn("### Tindakan berikutnya", commercial_brief(r))

    def test_alpha_only_changes_do_not_change_freight_economics(self):
        p = json.loads(GO.read_text(encoding="utf-8"))
        for b in p["bids"]:
            b["alpha_usd_mt"] = "-1"
        with tempfile.TemporaryDirectory() as t:
            r = evaluate(self.make_case(Path(t), p))
        original = evaluate(GO)
        self.assertEqual(r["baseline"], original["baseline"])
        self.assertEqual(r["metrics"], original["metrics"])
        self.assertEqual(r["recommendation"]["action"], "NO_GO")

    def test_higher_index_than_floor_has_negative_minimum_alpha(self):
        p = json.loads(GO.read_text(encoding="utf-8")); p["oe_hps"]["value"] = "410"
        with tempfile.TemporaryDirectory() as t:
            r = evaluate(self.make_case(Path(t), p))
        self.assertEqual(D(r["metrics"]["minimum_alpha_usd_mt"]), D(-5))
        self.assertIn("-5,00 USD/MT", commercial_brief(r))

    def test_frozen_record_preserved_and_invalid_data_cannot_be_frozen(self):
        r = evaluate(GO)
        self.assertEqual(fixed_freight_record(r), r["pricing"]["source_record"])
        with self.assertRaises(ValueError):
            fixed_freight_record({"recommendation": {"action": "NO_GO"}})

    def test_preparation_from_structured_case_without_raw_sources_and_no_overwrite(self):
        import importlib.util
        import contextlib
        import io
        spec = importlib.util.spec_from_file_location("prepare_i4_test", ROOT / "scripts/prepare_iteration_04.py")
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as t:
            dest = Path(t) / "prepared"
            with contextlib.redirect_stdout(io.StringIO()):
                module.prepare_case(GO, dest)
            r = evaluate(dest / GO.name)
            self.assertEqual(r["baseline"], evaluate(GO)["baseline"])
            self.assertEqual(r["pricing"]["source_record"], evaluate(GO)["pricing"]["source_record"])
            self.assertEqual((dest / CSV.name).read_bytes(), CSV.read_bytes())
            with self.assertRaises(ValueError):
                module.prepare_case(GO, dest)

    def test_internal_persisted_artifacts_and_json_brief_metrics_agree(self):
        r = evaluate(GO)
        with tempfile.TemporaryDirectory() as t:
            output = persist_run(r, Path(t))
            self.assertEqual({p.name for p in output.iterdir()}, {"commercial_decision_brief.md", "calculation_audit.md", "result.json", "input_snapshot"})
            saved = json.loads((output / "result.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["metrics"], r["metrics"])
            self.assertEqual(saved["classification"], "INTERNAL_NOT_FOR_BUYERS")
            self.assertTrue((output / "calculation_audit.md").is_file())
            self.assertIn("[Rincian perhitungan dan sumber]", (output / "commercial_decision_brief.md").read_text(encoding="utf-8"))

    def test_combined_shocks_do_not_reprice_or_become_an_unapproved_veto(self):
        p = json.loads(GO.read_text(encoding="utf-8"))
        p["scenarios"].append({"scenario_id": "combined", "label": "BBM dan delay bersamaan",
                               "fuel_price_increase_fraction": "0.25", "extra_port_days": "30", "source_status": "simulation_only_test"})
        with tempfile.TemporaryDirectory() as t:
            r = evaluate(self.make_case(Path(t), p))
        shock = next(s for s in r["scenarios"] if s["scenario_id"] == "combined")
        self.assertEqual(D(shock["economics"]["contribution_usd"]), D("-109798.7515625"))
        self.assertEqual(shock["economics"]["freight_usd_mt"], r["baseline"]["freight_usd_mt"])
        self.assertEqual(r["recommendation"]["action"], "GO")

    def test_preparing_legacy_case_derives_price_and_keeps_original_untouched(self):
        import importlib.util
        import contextlib
        import io
        spec = importlib.util.spec_from_file_location("prepare_i4_legacy_test", ROOT / "scripts/prepare_iteration_04.py")
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        p = json.loads(GO.read_text(encoding="utf-8")); p.pop("freight_tender", None)
        with tempfile.TemporaryDirectory() as t:
            folder = Path(t)
            source = self.make_case(folder, p)
            before = source.read_bytes()
            with contextlib.redirect_stdout(io.StringIO()):
                module.prepare_case(source, folder / "prepared")
            prepared = evaluate(folder / "prepared" / source.name)
            self.assertEqual(prepared["pricing"]["rate_mode"], "fixed_simulation")
            self.assertEqual(prepared["baseline"], evaluate(source)["baseline"])
            self.assertEqual(source.read_bytes(), before)

    def test_two_decimal_display_preserves_sign_and_gate_uses_raw_loss(self):
        self.assertEqual(amount("-0.00000001"), "-0,00")
        self.assertEqual(amount("0.00000001"), "0,00")
        payload = json.loads(GO.read_text(encoding="utf-8"))
        payload["freight_tender"]["value"] = "6"
        payload["pricing"]["target_tce"]["value"] = "100"
        overrides = {
            "cargo_mt": "100", "distance_nm": "240", "speed_knots": "10",
            "loading_rate_mt_day": "100", "discharge_rate_mt_day": "100",
            "sea_fo_mt_day": "0", "sea_do_mt_day": "0", "port_do_mt_day": "0",
            "running_usd_day": "100", "port_other_total_usd": "300.00000001",
            "freight_commission_fraction": "0", "broker_fraction": "0", "additional_commission_fraction": "0",
        }
        with tempfile.TemporaryDirectory() as temporary:
            result = evaluate(self.make_case(Path(temporary), payload, overrides))
        self.assertLess(D(result["baseline"]["contribution_usd"]), 0)
        self.assertEqual(result["recommendation"]["action"], "NO_GO")
        self.assertIn("-0,00", commercial_brief(result))


if __name__ == "__main__":
    unittest.main()
