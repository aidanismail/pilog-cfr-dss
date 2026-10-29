"""Commercial brief contract tests; temporary fixtures, never production inputs."""
import ast
import csv
import json
import sys
import tempfile
import unittest
from copy import deepcopy
from decimal import Decimal as D
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from pilog_cfr_dss.orchestration.iteration_04 import evaluate, persist_run
from pilog_cfr_dss.reporting.iteration_04 import commercial_brief, calculation_audit

GO = ROOT / "data/processed/i4_context.json"
NO = ROOT / "data/processed/i4_no_go.json"


def variant(context=None, overrides=None):
    payload = deepcopy(context) if context is not None else json.loads(GO.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as temp:
        folder = Path(temp)
        with (GO.parent / payload["voyage_dataset"]).open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream))
        for key, value in (overrides or {}).items():
            next(row for row in rows if row["key"] == key)["value"] = value
        with (folder / payload["voyage_dataset"]).open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        path = folder / "case.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return evaluate(path)


class CommercialBriefTests(unittest.TestCase):
    def test_five_ordered_lenses_and_financials_precede_supporting_details(self):
        headings = ["## 1. Keputusan komersial", "## 2. Eksposur ekonomi", "## 3. Risiko",
                    "## 4. Dampak logistik", "## 5. Konsekuensi harga"]
        for report in (evaluate(GO), evaluate(NO), variant(overrides={"speed_knots": "0"})):
            brief = commercial_brief(report)
            positions = [brief.index(heading) for heading in headings]
            self.assertEqual(positions, sorted(positions))
            if "baseline" in report:
                self.assertLess(brief.index("### Estimasi pendapatan"), positions[1])

    def test_all_bid_amounts_use_quantity_and_preserve_existing_economics(self):
        r = evaluate(GO)
        f = r["commercial_financials"]
        self.assertEqual(len(f["bid_amounts"]), len(r["tender"]["bids"]))
        self.assertEqual(D(f["pilog"]["net_after_voyage_usd"]), D(r["baseline"]["contribution_usd"]))
        self.assertNotEqual(f["pilog"]["net_after_voyage_usd"], r["baseline"]["net_revenue_usd"])
        q = D(r["case"]["cargo_mt"])
        for amounts, bid in zip(f["bid_amounts"], r["tender"]["bids"]):
            self.assertEqual(amounts["bid_id"], bid["bid_id"])
            self.assertEqual(D(amounts["pi_goods_gross_revenue_usd"]), D(bid["fob_usd_mt"]) * q)
            self.assertEqual(D(amounts["buyer_cfr_offer_value_usd"]), D(bid["cfr_usd_mt"]) * q)
            self.assertEqual(D(amounts["buyer_cfr_offer_value_usd"]), D(amounts["pi_goods_gross_revenue_usd"]) + D(amounts["pilog_gross_freight_revenue_usd"]))

    def test_alpha_changes_pi_gross_not_pilog_financials(self):
        original = evaluate(GO)
        p = json.loads(GO.read_text(encoding="utf-8"))
        p["bids"][-3]["alpha_usd_mt"] = "13"
        changed = variant(p)
        a, b = original["commercial_financials"], changed["commercial_financials"]
        self.assertEqual(a["pilog"], b["pilog"])
        self.assertNotEqual(a["bid_amounts"][-3]["pi_goods_gross_revenue_usd"], b["bid_amounts"][-3]["pi_goods_gross_revenue_usd"])

    def test_no_commodity_cost_or_pi_profit_is_invented_from_hps(self):
        r = evaluate(GO)
        self.assertIsNone(r["commercial_financials"]["pi"]["net_result_usd"])
        self.assertIsNone(r["commercial_financials"]["pi"]["goods_cost_usd"])
        brief = commercial_brief(r)
        self.assertIn("OE/HPS adalah batas harga barang, bukan biaya produksi", brief)
        self.assertIn("Neto PI tidak dihitung", brief)

    def test_clean_copy_preserves_factual_mode_sources_and_approval(self):
        r = evaluate(GO)
        brief = commercial_brief(r).lower()
        for unwanted in ("simulasi", "simulation", "butuh audit", "butuh pertimbangan", "perlu ditinjau"):
            self.assertNotIn(unwanted, brief)
        self.assertIn("bukan realisasi atau quotation pasar terkini", brief)
        self.assertIn("persetujuan manusia belum tercatat", brief)
        self.assertIn("belum terbukti", brief)
        self.assertEqual(r["mode"], "simulation")
        self.assertTrue(r["advisory_only"])
        self.assertIn("simulation_only", json.dumps(r["input_lineage"]))
        self.assertIn("Simulasi", calculation_audit(r))

    def test_no_active_bid_has_no_pi_gross_zero_or_fake_cfr_quote(self):
        p = json.loads(GO.read_text(encoding="utf-8"))
        for bid in p["bids"]:
            if bid["round"] == 3:
                bid["status"] = "withdrawn"
        brief = commercial_brief(variant(p))
        self.assertIn("Tidak tersedia — belum ada acuan bid yang valid", brief)
        self.assertNotIn("Nilai penawaran CFR", brief)

    def test_legacy_without_financial_summary_is_not_recomputed_by_renderer(self):
        r = evaluate(GO)
        r.pop("commercial_financials")
        self.assertIn("Ringkasan nominal per pihak tidak tersedia", commercial_brief(r))

    def test_go_headline_names_lot_candidate_and_relevant_amounts(self):
        report = evaluate(GO)
        header = commercial_brief(report).split("### Pemeriksaan keputusan", 1)[0]
        for text in ("# GO", "BUYER-1/R3-B1", "30.000,00 MT", "Bontang", "Mundra",
                     "427,00", "420,00", "24,90", "188.856,76", "-50.164,04"):
            self.assertIn(text, header)
        self.assertIn("bukan award", header)

    def test_no_go_floor_focuses_on_shortfall_and_labels_conditional_financials(self):
        report = evaluate(NO)
        brief = commercial_brief(report)
        header = brief.split("### Pemeriksaan keputusan", 1)[0]
        for text in ("# NO_GO", "BUYER-3/R3-B3", "401,00", "19,00", "Gate B belum dievaluasi"):
            self.assertIn(text, header)
        self.assertIn("Angka berikut hanya indikatif jika pengiriman terlaksana", brief)
        self.assertIn("bukan pendapatan terealisasi atau persetujuan melanjutkan", brief)
        self.assertIn("746.871,00", brief)
        self.assertIn("188.856,76", brief)
        self.assertIn("tidak menjadi dasar melewati pemeriksaan yang gagal", brief)
        self.assertIn("188856.76125000", calculation_audit(report))
        self.assertEqual(report["recommendation"]["gate_b"], "NOT_EVALUATED")

    def test_negative_economics_keeps_loss_and_costs_prominent(self):
        p = json.loads(GO.read_text(encoding="utf-8"))
        p["freight_tender"]["value"] = "1"
        report = variant(p)
        brief = commercial_brief(report)
        self.assertEqual(report["recommendation"]["brief_context"]["cause"], "NEGATIVE_ECONOMICS")
        self.assertIn("hasil neto setelah biaya voyage dan komisi", brief.lower())
        self.assertIn("kontribusi freight baseline negatif", brief)
        self.assertIn("baseline sudah rugi", brief)
        self.assertNotIn("Skenario rugi tidak membatalkan GO baseline", brief)
        self.assertIn("jangan menaikkan", report["recommendation"]["next_steps"][0]["deliverable"].lower())

    def test_each_action_requests_deliverable_trigger_without_faking_approval(self):
        for report in (evaluate(GO), evaluate(NO), variant(overrides={"speed_knots": "0"})):
            for step in report["recommendation"]["next_steps"]:
                with self.subTest(code=step["code"]):
                    self.assertTrue(step["deliverable"])
                    self.assertTrue(step["re_evaluate_when"])
                    self.assertEqual(step["review_evidence_status"], "NOT_RECORDED_IN_SIMULATION")
            brief = commercial_brief(report)
            self.assertIn("### Tindakan berikutnya", brief)
            self.assertIn("| Pemilik | Tindakan |", brief)
            self.assertIn("belum tercatat", brief)
            self.assertEqual(report["recommendation"]["human_approval"], "PENDING_HUMAN_REVIEW")

    def test_metadata_once_per_persist_matches_all_three_artifacts(self):
        report = evaluate(GO)
        with tempfile.TemporaryDirectory() as temp:
            output = persist_run(report, Path(temp))
            saved = json.loads((output / "result.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["run_id"], output.name)
            self.assertIn("+00:00", saved["generated_at"])
            for filename in ("commercial_decision_brief.md", "calculation_audit.md"):
                text = (output / filename).read_text(encoding="utf-8")
                self.assertIn(saved["run_id"], text)
                self.assertIn(saved["generated_at"], text)
                self.assertIn("2026-09-10T12:00:00+00:00", text)
            self.assertEqual(saved["report_version"], "I4-BRIEF.4")
            self.assertEqual(saved["version"], "I4.1")
            self.assertNotIn("run_id", report)  # Do not mutate evaluated input/report.

    def test_render_does_not_change_saved_identity_or_values(self):
        with tempfile.TemporaryDirectory() as temp:
            output = persist_run(evaluate(GO), Path(temp))
            raw = (output / "result.json").read_bytes()
            report = json.loads(raw)
            first, second = commercial_brief(report), commercial_brief(report)
            self.assertEqual(first, second)
            self.assertEqual((output / "result.json").read_bytes(), raw)
            self.assertEqual(json.loads(calculation_audit(report).split("~~~json")[1].split("~~~")[0]), report)

    def test_legacy_metadata_is_not_guessed_from_current_clock(self):
        report = evaluate(GO)
        report["report_version"] = "I4-BRIEF.2"
        report["recommendation"].pop("brief_context")
        for step in report["recommendation"]["next_steps"]:
            for key in ("deliverable", "re_evaluate_when", "review_evidence_status"):
                step.pop(key)
        brief = commercial_brief(report)
        self.assertIn("Dibuat (UTC): Tidak tersedia", brief)
        self.assertIn("BUYER-1/R3-B1", brief)
        self.assertIn("I4-BRIEF.2", brief)
        self.assertIn("metadata historis", brief)

    def test_tie_shows_all_candidates_in_headline_without_award(self):
        p = json.loads(GO.read_text(encoding="utf-8"))
        p["bids"][-2]["alpha_usd_mt"] = "12"
        report = variant(p)
        header = commercial_brief(report).split("### Pemeriksaan keputusan", 1)[0]
        self.assertIn("BUYER-1/R3-B1, BUYER-2/R3-B2", header)
        self.assertEqual(report["tender"]["award_status"], "NOT_AWARDED_BY_SYSTEM")
        self.assertEqual(len(report["recommendation"]["brief_context"]["candidate_bids"]), 2)

    def test_eligible_pi_selection_is_not_silently_replaced_by_rank_one(self):
        p = json.loads(GO.read_text(encoding="utf-8")); p["pi_selected_bid_id"] = "R3-B2"
        report = variant(p)
        header = commercial_brief(report).split("### Pemeriksaan keputusan", 1)[0]
        self.assertIn("BUYER-2/R3-B2", header)
        self.assertIn("423,00", header)
        self.assertNotIn("BUYER-1/R3-B1", header)
        self.assertEqual(report["recommendation"]["brief_context"]["selection_basis"], "PI_SELECTION")

    def test_invalid_selection_does_not_claim_all_active_bids_failed_floor(self):
        p = json.loads(GO.read_text(encoding="utf-8")); p["pi_selected_bid_id"] = "R1-B1"
        report = variant(p)
        self.assertEqual(report["recommendation"]["brief_context"]["cause"], "PI_SELECTION")
        self.assertTrue(report["tender"]["ranking"])
        header = commercial_brief(report).split("### Pemeriksaan keputusan", 1)[0]
        self.assertIn("pilihan PI", header)
        self.assertNotIn("tidak ada bid terakhir aktif yang memenuhi syarat", header)

    def test_no_active_bids_do_not_invent_best_price_or_shortfall(self):
        p = json.loads(GO.read_text(encoding="utf-8"))
        for bid in p["bids"]:
            if bid["round"] == 3:
                bid["status"] = "withdrawn"
        report = variant(p)
        self.assertEqual(report["recommendation"]["brief_context"]["cause"], "NO_ACTIVE_BID")
        header = commercial_brief(report).split("### Pemeriksaan keputusan", 1)[0]
        self.assertIn("Tidak ada bid aktif", header)
        self.assertNotIn("FOB **", header)
        self.assertFalse(report["tender"]["candidate_bid_ids"])

    def test_multiple_failures_are_visible_not_hidden_by_a_primary_reason(self):
        p = json.loads(GO.read_text(encoding="utf-8")); p["freight_tender"]["value"] = "1"
        report = variant(p, {"dwt_mt": "25000"})
        self.assertEqual(report["recommendation"]["brief_context"]["cause"], "VESSEL_AND_ECONOMICS")
        brief = commercial_brief(report)
        self.assertIn("kapal tidak lolos", brief)
        self.assertIn("kontribusi freight baseline negatif", brief)
        codes = [s["code"] for s in report["recommendation"]["next_steps"]]
        self.assertIn("REVIEW_VESSEL_SCREEN", codes)
        self.assertIn("REVIEW_BASELINE_COST", codes)

    def test_data_issue_does_not_print_fake_case_price_or_zero_economics(self):
        report = variant(overrides={"speed_knots": "0"})
        brief = commercial_brief(report)
        self.assertIn("# NO_GO", brief)
        self.assertIn("NONPOSITIVE_INPUT:speed_knots", brief)
        self.assertIn("tidak ada kandidat/angka pengganti nol", brief)
        self.assertNotIn("24,90", brief)
        self.assertNotIn("### Estimasi pendapatan, biaya dan hasil neto", brief)
        self.assertNotIn("Kandidat review:", brief)

    def test_vessel_only_failure_is_not_overshadowed_by_positive_economics(self):
        report = variant(overrides={"dwt_mt": "25000"})
        self.assertEqual(report["recommendation"]["brief_context"]["cause"], "VESSEL_SCREEN")
        brief = commercial_brief(report)
        self.assertIn("Screen kapal gagal", brief)
        self.assertIn("Angka berikut hanya indikatif", brief)
        self.assertIn("Hasil freight positif tidak membuat kapal lolos", brief)

    def test_commission_basis_and_pi_pilog_distinction_are_explicit(self):
        brief = commercial_brief(evaluate(GO))
        self.assertIn("Komisi 6,25% × gross freight revenue", brief)
        self.assertIn("alpha tidak otomatis mengubah kontribusi freight PILOG", brief)
        self.assertIn("bukan laba bersih", brief)

    def test_no_stress_scenarios_is_not_presented_as_risk_free(self):
        p = json.loads(GO.read_text(encoding="utf-8")); p["scenarios"] = []
        report = variant(p)
        self.assertIsNone(report["recommendation"]["brief_context"]["primary_stress"])
        self.assertIn("baseline bukan bukti risiko nol", commercial_brief(report))

    def test_exact_break_even_is_go_but_not_called_profitable(self):
        p = json.loads(GO.read_text(encoding="utf-8"))
        p["freight_tender"]["value"] = "6"
        p["pricing"]["target_tce"]["value"] = "100"
        report = variant(p, {"cargo_mt": "100", "distance_nm": "240", "speed_knots": "10",
                            "loading_rate_mt_day": "100", "discharge_rate_mt_day": "100",
                            "sea_fo_mt_day": "0", "sea_do_mt_day": "0", "port_do_mt_day": "0",
                            "running_usd_day": "100", "port_other_total_usd": "300",
                            "freight_commission_fraction": "0", "broker_fraction": "0", "additional_commission_fraction": "0"})
        self.assertEqual(report["recommendation"]["action"], "GO")
        self.assertEqual(report["recommendation"]["brief_context"]["cause"], "GO_BREAK_EVEN")
        header = commercial_brief(report).split("### Pemeriksaan keputusan", 1)[0]
        self.assertIn("Baseline tepat impas", header)
        self.assertIn("bukan berarti untung", header)

    def test_renderer_has_no_financial_operators_or_wall_clock(self):
        source = (ROOT / "src/pilog_cfr_dss/reporting/iteration_04.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        self.assertFalse(any(isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Div, ast.Mult, ast.Sub, ast.Pow)) for n in ast.walk(tree)))
        self.assertNotIn("datetime", source)
        self.assertNotIn("required_freight(", source)


if __name__ == "__main__":
    unittest.main()
