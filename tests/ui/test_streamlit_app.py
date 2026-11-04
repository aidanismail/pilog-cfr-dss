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

    def test_output_exposes_fixed_rate_sensitivity(self):
        next(x for x in self.app.button if x.label == "Hitung ekonomi voyage").click().run()
        self.assertFalse(self.app.exception)
        result = self.app.session_state["case"].preparation
        self.assertTrue(result["fixed_freight_sensitivities"])
        self.assertTrue(all(x["economics"]["freight_usd_mt"] == result["baseline"]["freight_usd_mt"]
                            for x in result["fixed_freight_sensitivities"]))
        self.assertTrue(any(x.label == "TCE hasil voyage (USD/hari)" for x in self.app.metric))
        self.assertFalse(any(x.label == "Target TCE (USD/hari)" for x in self.app.metric))
