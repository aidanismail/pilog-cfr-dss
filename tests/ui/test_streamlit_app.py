"""Active I5 UI contract; tender/brief logic is covered by engine regressions."""
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
from pilog_cfr_dss.sources.fearnpulse import latest_saved

ROOT = Path(__file__).resolve().parents[2]


class StreamlitWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.env = patch.dict(os.environ, {"PILOG_UI_OUTPUT_ROOT": self.temp.name})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.market = patch("pilog_cfr_dss.ui.views._fresh_market", return_value=latest_saved(ROOT))
        self.market.start()
        self.addCleanup(self.market.stop)
        self.baltic = patch("pilog_cfr_dss.ui.views._baltic_check", return_value={"source_status": "test"})
        self.baltic.start()
        self.addCleanup(self.baltic.stop)
        self.app = AppTest.from_file(str(ROOT / "apps/streamlit_app.py"), default_timeout=30).run()
        self.assertFalse(self.app.exception)

    def test_case_has_no_award_or_fake_result_and_market_dates_visible(self):
        case = self.app.session_state["case"]
        self.assertFalse(case.fixed)
        self.assertIsNone(case.preparation)
        self.assertEqual(case.context["bids"], [])
        self.assertTrue(any("Fearnpulse diambil:" in x.value for x in self.app.caption))
        self.assertEqual(case.context["capacity_basis"], "dataset_allowances_v1")
        self.assertFalse(any(x.label == "Evaluasi tender & DSS" for x in self.app.button))

    def test_workspace_download_replaces_shared_draft_listing(self):
        self.assertTrue(any(x.label == "Unduh kasus" for x in self.app.get("download_button")))
        self.assertFalse(any(x.label == "Buka draft tersimpan" for x in self.app.selectbox))

    def test_hire_input_is_editable_and_survives_class_switch(self):
        frame = next(f.value for f in self.app.dataframe if 'Parameter' in f.value.columns)
        hire_index = next(i for i, name in enumerate(frame['Parameter']) if name.startswith('Hire/day'))
        self.assertEqual(frame.iloc[hire_index]['Nilai'], 13000)
        self.assertIn('historis', frame.iloc[hire_index]['Sumber'])
        self.assertFalse(any('operasional kapal harian' in name.lower() for name in frame['Parameter']))
        case = self.app.session_state['case']
        key = f'inputs_table_{case.draft_id}_{case.revision}_None'
        self.app.session_state[key] = {'edited_rows': {hire_index: {'Nilai': 18000.5}}, 'added_rows': [], 'deleted_rows': []}
        self.app.run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.session_state['case'].values()['hire_usd_day'], '18000.5')
        selector = next(x for x in self.app.selectbox if x.label == 'Pilih profil kapal')
        selector.set_value('ve_godau').run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.session_state['case'].values()['hire_usd_day'], '18000.5')
        next(x for x in self.app.button if x.label == 'Hitung ekonomi voyage').click().run()
        self.assertFalse(self.app.exception)
        result = self.app.session_state['case'].preparation
        self.assertIn('tce_usd_day', result['baseline'])
        self.assertNotIn('running_usd', result['baseline'])

    def test_hire_and_tce_are_visible_and_running_cost_is_absent_from_results(self):
        next(x for x in self.app.button if x.label == 'Hitung ekonomi voyage').click().run()
        self.assertFalse(self.app.exception)
        components = [str(value) for frame in self.app.dataframe if 'Komponen' in frame.value.columns
                      for value in frame.value['Komponen']]
        self.assertIn('Hire kapal', components)
        self.assertIn('Net freight revenue', components)
        self.assertFalse(any('Operasional kapal' in value or 'Running' in value for value in components))
        self.assertTrue(any('TCE sebelum hire' in item.value for item in self.app.caption))
        self.assertTrue(any('net freight revenue − voyage expenses' in item.value for item in self.app.markdown))

    def test_legacy_session_explains_cost_model_instead_of_silent_conversion(self):
        from pilog_cfr_dss.application.interactive_case import InteractiveCase
        legacy = InteractiveCase.read(ROOT / 'data/processed/case_template.json')
        before = legacy.fingerprint
        self.app.session_state['case'] = legacy
        self.app.run()
        self.assertFalse(self.app.exception)
        self.assertTrue(any('model kapal milik sebelumnya' in item.value for item in self.app.warning))
        self.assertFalse(any(x.label == 'Hitung ekonomi voyage' for x in self.app.button))
        self.assertEqual(self.app.session_state['case'].fingerprint, before)
        next(x for x in self.app.button if x.label == 'Kasus baru').click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.session_state['case'].values()['vessel_mode'], 'chartered')

    def test_output_exposes_fixed_rate_sensitivity(self):
        next(x for x in self.app.button if x.label == "Hitung ekonomi voyage").click().run()
        self.assertFalse(self.app.exception)
        result = self.app.session_state["case"].preparation
        self.assertTrue(result["fixed_freight_sensitivities"])
        self.assertTrue(all(x["economics"]["freight_usd_mt"] == result["baseline"]["freight_usd_mt"]
                            for x in result["fixed_freight_sensitivities"]))
        self.assertTrue(any(x.label == "TCE hasil voyage (USD/hari)" for x in self.app.metric))
        self.assertFalse(any(x.label == "Target TCE (USD/hari)" for x in self.app.metric))
        self.assertTrue(any('Kenaikan harga bunker (%)' in frame.value.columns and
                            'Tambahan waktu pelabuhan (hari)' in frame.value.columns
                            for frame in self.app.dataframe))

    def test_one_failed_report_is_distinct_from_missing_assessment(self):
        with patch('pilog_cfr_dss.sources.market_comparables.read_comparables', side_effect=ValueError('unreadable')):
            next(x for x in self.app.button if x.label == 'Hitung ekonomi voyage').click().run()
        self.assertFalse(self.app.exception)
        self.assertTrue(any('Laporan Fertecon belum dapat dibaca' in item.value for item in self.app.warning))
        self.assertTrue(any('Kecocokan' in frame.value.columns for frame in self.app.dataframe))

    def test_editing_speed_warns_that_consumption_is_not_automatically_changed(self):
        case = self.app.session_state['case']
        initial_fo = case.values()['sea_fo_mt_day']
        key = f'inputs_table_{case.draft_id}_{case.revision}_None'
        self.app.session_state[key] = {'edited_rows': {7: {'Nilai': 13.0}}, 'added_rows': [], 'deleted_rows': []}
        self.app.run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.session_state['case'].values()['sea_fo_mt_day'], initial_fo)
        self.assertTrue(any('konsumsi bahan bakar tidak berubah otomatis' in item.value for item in self.app.caption))
