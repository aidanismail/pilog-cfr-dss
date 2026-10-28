import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

AVAILABLE = importlib.util.find_spec("streamlit") is not None
if AVAILABLE:
    from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "apps/streamlit_app.py"


@unittest.skipUnless(AVAILABLE, "Optional UI: install requirements-ui.txt")
class StreamlitWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.environment = patch.dict(os.environ, {"PILOG_UI_OUTPUT_ROOT": self.temp.name})
        self.environment.start(); self.addCleanup(self.environment.stop)
        self.app = AppTest.from_file(str(APP), default_timeout=25).run()
        self.assertFalse(self.app.exception)

    def click(self, label):
        next(button for button in self.app.button if button.label == label).click().run()
        self.assertFalse(self.app.exception)

    def toggle(self, label, value):
        next(toggle for toggle in self.app.toggle if toggle.label == label).set_value(value).run()
        self.assertFalse(self.app.exception)

    def test_initial_state_no_fake_bid_no_result_no_run(self):
        case = self.app.session_state["case"]
        self.assertEqual(case.context["bids"], [])
        self.assertIsNone(case.result)
        self.assertFalse(case.fixed)
        self.assertFalse((Path(self.temp.name) / "runs").exists())

    def test_new_case_preparation_fixed_tender_and_go(self):
        self.click("Hitung ekonomi voyage")
        self.assertIsNotNone(self.app.session_state["case"].preparation)
        self.click("Tetapkan freight untuk tender")
        self.toggle("Edit bid & risiko", True)
        self.click("Isi contoh bid tiga putaran")
        self.click("Terapkan bid & risiko")
        self.click("Evaluasi tender & DSS")
        case = self.app.session_state["case"]
        self.assertEqual(case.result["recommendation"]["action"], "GO")
        self.assertTrue((case.run_dir / "result.json").exists())

    def test_loaded_go_and_no_go_examples_use_real_engine(self):
        for label, expected in (("Muat contoh GO", "GO"), ("Muat contoh NO GO", "NO_GO")):
            self.click(label)
            self.click("Evaluasi tender & DSS")
            result = self.app.session_state["case"].result
            self.assertEqual(result["recommendation"]["action"], expected)
        self.assertEqual(result["recommendation"]["gate_b"], "NOT_EVALUATED")

    def test_edit_mode_hides_result_and_disables_evaluation(self):
        self.click("Muat contoh GO"); self.click("Evaluasi tender & DSS")
        self.toggle("Edit bid & risiko", True)
        button = next(button for button in self.app.button if button.label == "Evaluasi tender & DSS")
        self.assertTrue(button.disabled)
        self.assertTrue(any("Editor aktif" in caption.value for caption in self.app.caption))
        self.assertFalse(self.app.get("download_button"))

    def test_rerun_and_draft_save_do_not_duplicate_runs(self):
        self.click("Muat contoh GO"); self.click("Evaluasi tender & DSS")
        case = self.app.session_state["case"]
        run = case.run_dir
        self.app.run(); self.click("Simpan draft"); self.app.run()
        self.assertEqual(case.run_dir, run)
        self.assertEqual(len(list((Path(self.temp.name) / "runs").iterdir())), 1)

    def test_input_edit_apply_changes_value_and_closes_editor(self):
        self.toggle("Ubah input kasus", True)
        next(item for item in self.app.text_input if item.label == "Harga diesel oil (USD/MT)").set_value("799.1234")
        self.click("Terapkan input")
        self.assertEqual(self.app.session_state["case"].values()["do_price_usd_mt"], "799.1234")
        self.assertFalse(next(toggle for toggle in self.app.toggle if toggle.label == "Ubah input kasus").value)
        self.click("Hitung ekonomi voyage")
        self.assertIsNotNone(self.app.session_state["case"].preparation)

    def test_critical_data_issue_renders_no_go_without_exception(self):
        self.click("Muat contoh GO")
        self.app.session_state["case"].context["bids"][-1]["alpha_usd_mt"] = "NaN"
        self.click("Evaluasi tender & DSS")
        result = self.app.session_state["case"].result
        self.assertIn("DATA_ISSUE", result["recommendation"]["reason_codes"])
        self.assertEqual(result["recommendation"]["action"], "NO_GO")

    def test_profile_dropdown_switches_complete_workbook_package(self):
        for profile_id, expected_class in (("ve_aqaba", "Supramax"), ("ve_sby", "Supramax"), ("ve_godau", "Handymax"), ("ve_sheet1", "Handysize")):
            self.assertEqual(len([select for select in self.app.selectbox if select.label == "Pilih profil kapal"]), 1)
            next(select for select in self.app.selectbox if select.label == "Pilih profil kapal").set_value(profile_id).run()
            self.assertFalse(self.app.exception)
            case = self.app.session_state["case"]
            self.assertEqual(case.context["vessel_profile"]["profile_id"], profile_id)
            self.assertEqual(case.values()["vessel_class"], expected_class)
            self.assertIsNone(case.preparation)
            expected_family = "Supramax" if expected_class == "Supramax" else "Handysize"
            self.assertEqual(case.context["pricing"]["target_tce"]["value"], case.context["market_snapshot"]["tc_rates"][expected_family]["value"])
            self.assertTrue(any(expected_class + " · " + case.context["vessel_profile"]["sheet"] + " → acuan" in caption.value for caption in self.app.caption))

    def test_comparison_and_compact_source_copy(self):
        self.click("Bandingkan profil")
        self.assertEqual(len(self.app.session_state["profile_comparison"]["rows"]), 4)
        captions = " ".join(item.value for item in self.app.caption)
        self.assertNotIn("Kasus UI-", captions)
        self.assertNotIn("mentor", captions.lower())
        self.assertNotIn("baltic", captions.lower())
        self.assertTrue(any("Tanggal data" in str(frame.value) for frame in self.app.dataframe))

    def test_fetch_then_apply_creates_revision_without_repricing_fixed(self):
        self.click("Muat contoh GO")
        original = self.app.session_state["case"]
        fixed = original.context["freight_tender"].copy()
        from copy import deepcopy
        fetched = deepcopy(original.context["market_snapshot"])
        fetched["snapshot_id"] = "fp_new_ui_test_snapshot"
        with patch("pilog_cfr_dss.ui.views.fetch_snapshot", return_value=fetched), patch("pilog_cfr_dss.ui.views.save_snapshot"):
            self.click("Perbarui data Fearnpulse")
        self.assertEqual(original.context["freight_tender"], fixed)
        self.click("Gunakan data pasar pada kasus baru")
        revised = self.app.session_state["case"]
        self.assertFalse(revised.fixed)
        self.assertEqual(revised.context["bids"], [])
        self.assertEqual(revised.context["market_snapshot"]["snapshot_id"], fetched["snapshot_id"])
        self.assertEqual(original.context["freight_tender"], fixed)

    def test_tender_tables_separate_rounds_and_show_computed_prices(self):
        self.click("Muat contoh GO")
        frames = [frame.value for frame in self.app.dataframe if "CFR (USD/MT)" in frame.value.columns]
        self.assertEqual(len(frames), 3)
        self.assertTrue(all(len(frame) == 3 for frame in frames))
        case = self.app.session_state["case"]
        rows = case.tender_preview()
        from decimal import Decimal
        for index, frame in enumerate(frames, 1):
            expected = [r for r in rows if r["round"] == index]
            self.assertEqual(list(frame["Buyer"]), [r["buyer_id"] for r in expected])
            from decimal import ROUND_HALF_UP
            self.assertEqual([Decimal(v.replace(".", "").replace(",", ".")) for v in frame["CFR (USD/MT)"]],
                             [Decimal(r["cfr_usd_mt"]).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) for r in expected])
        captions = " ".join(item.value for item in self.app.caption)
        self.assertNotIn("Periksa sumber dan basis", captions)
        self.assertNotIn("Tarif OD", captions)

    def test_adding_empty_fourth_editor_round_preserves_bids_and_fixed_rate(self):
        from copy import deepcopy
        self.click("Muat contoh GO")
        case = self.app.session_state["case"]
        original = deepcopy(case.context["bids"])
        fixed = deepcopy(case.context["freight_tender"])
        self.toggle("Edit bid & risiko", True)
        self.click("Tambah putaran")
        self.assertTrue(any(item.value == "#### Putaran 4" for item in self.app.markdown))
        self.click("Terapkan bid & risiko")
        normalized = [{k: v for k, v in row.items() if k != "source_status"} for row in case.context["bids"]]
        self.assertEqual(normalized, [{k: v for k, v in row.items() if k != "source_status"} for row in original])
        self.assertEqual(case.context["freight_tender"], fixed)
        self.click("Evaluasi tender & DSS")
        self.assertEqual(case.result["recommendation"]["action"], "GO")

    def test_source_bound_distance_and_zero_commissions_are_read_only(self):
        self.toggle("Ubah input kasus", True)
        for label in ("Jarak satu arah (NM)", "Komisi freight (fraksi)", "Komisi broker (fraksi)", "Komisi tambahan (fraksi)"):
            item = next(item for item in self.app.text_input if item.label == label)
            self.assertTrue(item.disabled)
        self.assertTrue(all(self.app.session_state["case"].values()[key] == "0" for key in
            ("freight_commission_fraction", "broker_fraction", "additional_commission_fraction")))

    def test_cost_reforecast_changes_go_to_economic_no_go_same_quote_and_bids(self):
        from copy import deepcopy
        self.click("Muat contoh GO"); self.click("Evaluasi tender & DSS")
        original = self.app.session_state["case"]
        quote = deepcopy(original.context["freight_tender"]); bids = deepcopy(original.context["bids"])
        self.toggle("Perbarui estimasi biaya", True)
        self.assertTrue(next(button for button in self.app.button if button.label == "Evaluasi tender & DSS").disabled)
        self.assertTrue(next(toggle for toggle in self.app.toggle if toggle.label == "Edit bid & risiko").disabled)
        self.assertFalse(self.app.get("download_button"))
        next(item for item in self.app.text_input if item.label == "Total pelabuhan dan biaya lain (USD) — estimasi terbaru").set_value("450000")
        next(item for item in self.app.text_area if item.label == "Alasan perubahan biaya").set_value("Synthetic updated port estimate")
        self.click("Terapkan estimasi biaya")
        changed = self.app.session_state["case"]
        self.assertEqual(changed.context["freight_tender"], quote)
        self.assertEqual(changed.context["bids"], bids)
        self.assertIsNone(changed.result)
        self.click("Evaluasi tender & DSS")
        self.assertEqual((changed.result["recommendation"]["gate_a"], changed.result["recommendation"]["gate_b"]), ("PASS", "FAIL"))
        self.assertEqual(original.result["recommendation"]["action"], "GO")

    def test_invalid_cost_reforecast_does_not_replace_case(self):
        self.click("Muat contoh GO")
        original = self.app.session_state["case"]
        self.toggle("Perbarui estimasi biaya", True)
        self.click("Terapkan estimasi biaya")
        self.assertTrue(any("REASON_REQUIRED" in item.value for item in self.app.error))
        self.assertEqual(self.app.session_state["case"].draft_id, original.draft_id)

    def test_manual_offer_is_distinct_from_indication_and_can_be_no_go(self):
        self.click("Hitung ekonomi voyage")
        next(item for item in self.app.text_input if item.label == "Freight penawaran (USD/MT)").set_value("10")
        next(item for item in self.app.text_input if item.label == "Alasan jika berbeda dari indikasi").set_value("Synthetic test offer")
        self.click("Tetapkan freight untuk tender")
        self.toggle("Edit bid & risiko", True); self.click("Isi contoh bid tiga putaran")
        self.click("Terapkan bid & risiko"); self.click("Evaluasi tender & DSS")
        result = self.app.session_state["case"].result
        self.assertEqual(result["recommendation"]["gate_a"], "PASS")
        self.assertEqual(result["recommendation"]["action"], "NO_GO")
        self.assertEqual(result["pricing"]["freight_tender_usd_mt"], "10")

    def test_economic_demo_and_same_price_comparison_are_available(self):
        self.click("Muat NO GO ekonomi"); self.click("Evaluasi tender & DSS")
        result = self.app.session_state["case"].result
        self.assertEqual(result["recommendation"]["action"], "NO_GO")
        self.assertEqual(result["recommendation"]["gate_a"], "PASS")
        self.click("Bandingkan profil")
        rows = self.app.session_state["profile_comparison"]["rows"]
        self.assertEqual(len({row["common_freight_usd_mt"] for row in rows}), 1)
        self.assertTrue(all("common_contribution_per_day_usd" in row for row in rows))

    def test_manual_bunker_price_is_visible_and_used_in_voyage(self):
        self.toggle("Ubah input kasus", True)
        next(item for item in self.app.text_input if item.label == "Harga diesel oil (USD/MT)").set_value("799.1234")
        self.click("Terapkan input")
        frame = next(frame.value for frame in self.app.dataframe if "Bahan bakar" in frame.value.columns)
        diesel = frame[frame["Bahan bakar"] == "Diesel oil"].iloc[0]
        self.assertEqual(diesel["Sumber nilai"], "Input manual")
        self.assertEqual(diesel["Harga dipakai (USD/MT)"], "799,12")
        self.click("Hitung ekonomi voyage")
        case = self.app.session_state["case"]
        costs = next(frame.value for frame in self.app.dataframe if "Komponen" in frame.value.columns and "USD" in frame.value.columns)
        from pilog_cfr_dss.ui.views import fmt
        self.assertEqual(costs[costs["Komponen"] == "Diesel oil"].iloc[0]["USD"], fmt(case.preparation["baseline"]["do_cost_usd"]))

    def test_reforecast_sources_show_effective_bunker_and_operating_values(self):
        self.click("Muat contoh GO")
        original = self.app.session_state["case"]
        changed = original.reforecast_costs({"fo_price_usd_mt": "700", "speed_knots": "10"}, "Synthetic active-input check")
        self.app.session_state["case"] = changed
        self.app.run()
        self.assertFalse(self.app.exception)
        bunker = next(frame.value for frame in self.app.dataframe if "Bahan bakar" in frame.value.columns)
        fuel = bunker[bunker["Bahan bakar"] == "Fuel oil"].iloc[0]
        self.assertEqual((fuel["Harga dipakai (USD/MT)"], fuel["Sumber nilai"]), ("700,00", "Estimasi terbaru"))
        vessel = next(frame.value for frame in self.app.dataframe if "Spesifikasi" in frame.value.columns)
        self.assertEqual(vessel[vessel["Spesifikasi"] == "Kecepatan bermuatan"].iloc[0]["Nilai"], "10,00")
        self.assertEqual(original.values()["speed_knots"], "12")
        self.assertNotEqual(original.values()["fo_price_usd_mt"], "700")
        self.click("Hitung ekonomi voyage")
        durations = next(frame.value for frame in self.app.dataframe if "Komponen" in frame.value.columns and "Satuan" in frame.value.columns)
        from pilog_cfr_dss.ui.views import fmt
        self.assertEqual(durations[durations["Komponen"] == "Fuel oil saat berlayar"].iloc[0]["Nilai"], fmt(changed.preparation["baseline"]["fo_mt"]))

    def test_supporting_analysis_matches_engine_without_repeated_footer(self):
        self.click("Muat NO GO ekonomi")
        self.click("Evaluasi tender & DSS")
        report = self.app.session_state["case"].result
        frame = next(frame.value for frame in self.app.dataframe if "Skenario" in frame.value.columns)
        from pilog_cfr_dss.ui.views import fmt
        self.assertEqual(list(frame["Kontribusi PILOG (USD)"]), [fmt(row["economics"]["contribution_usd"]) for row in report["scenarios"]])
        labels = {metric.label: metric.value for metric in self.app.metric}
        self.assertEqual(labels["Freight impas (USD/MT)"], fmt(report["commercial_review"]["break_even_offer_usd_mt"], minimum=True))
        self.assertTrue(any("Singapura adalah acuan harga, bukan lokasi bunkering" in caption.value for caption in self.app.caption))
        self.assertTrue(any("Cakupan lanjutan: probabilitas" in caption.value for caption in self.app.caption))
        self.assertFalse(any("Hasil mengacu pada input terakhir" in caption.value for caption in self.app.caption))
        self.assertEqual(len(self.app.get("download_button")), 3)

    def test_profile_cannot_change_while_editing_or_after_quote_fixed(self):
        self.toggle("Ubah input kasus", True)
        self.assertTrue(next(select for select in self.app.selectbox if select.label == "Pilih profil kapal").disabled)
        self.toggle("Ubah input kasus", False)
        self.assertFalse(next(select for select in self.app.selectbox if select.label == "Pilih profil kapal").disabled)
        self.click("Muat contoh GO")
        self.assertTrue(next(select for select in self.app.selectbox if select.label == "Pilih profil kapal").disabled)
