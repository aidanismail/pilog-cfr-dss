"""Freight Desk UI tests. Historical auction UI tests retired with tender scope."""
from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import patch
from datetime import datetime
from zoneinfo import ZoneInfo
from streamlit.testing.v1 import AppTest
from pilog_cfr_dss.sources.fearnpulse import latest_saved
from pilog_cfr_dss.application.freight_desk import override

ROOT=Path(__file__).resolve().parents[2]


class FreightDeskUITests(unittest.TestCase):
    def setUp(self):
        self.market=latest_saved(ROOT)
        self.patcher=patch("pilog_cfr_dss.ui.views.fetch_snapshot",return_value=self.market)
        self.market_mock=self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.kobc = patch("pilog_cfr_dss.ui.views.fetch_kobc", return_value={"classes": {}, "errors": {}})
        self.kobc_mock = self.kobc.start()
        self.addCleanup(self.kobc.stop)
        baltic = patch("pilog_cfr_dss.ui.views.verify_benchmarks",
                       return_value={"url": "https://www.balticexchange.com/",
                                     "checked_at": "2026-11-20T00:00:00Z", "status": "verified"})
        self.baltic_mock = baltic.start()
        self.addCleanup(baltic.stop)
        kobc_storage = patch("pilog_cfr_dss.ui.views.remember_kobc", side_effect=lambda quote, _: quote)
        kobc_storage.start()
        self.addCleanup(kobc_storage.stop)
        self.storage=patch("pilog_cfr_dss.ui.views.save_runtime_snapshot")
        self.storage.start()
        self.addCleanup(self.storage.stop)
        self.app=AppTest.from_file(str(ROOT/"apps/streamlit_app.py"),default_timeout=30).run()
        self.assertFalse(list(self.app.exception))

    def button(self,name):
        return next(x for x in self.app.button if x.label==name)

    def choose(self,label,value,index=0):
        [x for x in self.app.selectbox if x.label==label][index].set_value(value).run()

    def test_initial_inputs_and_no_tender(self):
        self.assertEqual(len([x for x in self.app.selectbox if x.label=="Terms"]),2)
        self.assertEqual(len([x for x in self.app.selectbox if x.label=="Terms"][0].options),23)
        with self.assertRaises(KeyError):
            self.app.session_state["freight_result"]
        self.assertFalse(any("bid" in x.label.lower() for x in self.app.button))

    def test_kobc_hire_per_class_and_manual_edit(self):
        from tests.unit.test_kobc import quote
        today = datetime.now(ZoneInfo("Asia/Seoul")).date().isoformat()
        self.kobc_mock.return_value = {"classes": {family: quote(family, today)
                                for family in ("Handysize", "Supramax")}, "errors": {}}
        del self.app.session_state["online_inputs"]
        self.app.run()
        case = self.app.session_state["freight_case"]
        self.assertEqual(case["profiles"]["Handysize"]["hire_usd_day"], "16000")
        self.assertEqual(case["profiles"]["Supramax"]["hire_usd_day"], "22000")
        self.button("Hitung freight").click().run()
        self.assertFalse(list(self.app.exception))
        result = self.app.session_state["freight_result"]
        self.assertEqual(str(result["classes"]["Handysize"]["nominal"]["hire_rate_usd_day"]), "16000")
        override(case, "profiles.Handysize.hire_usd_day", "12500")
        self.app.run()
        self.assertEqual(case["profiles"]["Handysize"]["hire_usd_day"], "12500")

    def test_new_streamlit_session_refetches_all_three_sources(self):
        self.app.run()
        for provider in (self.market_mock, self.kobc_mock, self.baltic_mock):
            self.assertEqual(provider.call_count, 1)
        reloaded = AppTest.from_file(str(ROOT / "apps/streamlit_app.py"), default_timeout=30).run()
        self.assertFalse(list(reloaded.exception))
        for provider in (self.market_mock, self.kobc_mock, self.baltic_mock):
            self.assertEqual(provider.call_count, 2)

    def test_calculate_brief_metrics_and_matrix(self):
        self.button("Hitung freight").click().run()
        self.assertFalse(list(self.app.exception))
        self.assertTrue(self.app.metric)
        self.assertIn("Minimum penawaran USD/MT",[x.label for x in self.app.metric])
        self.assertIn("Commercial brief",[x.label for x in self.app.expander])
        self.assertFalse(any(x.label == "Hitung matrix" for x in self.app.button))
        self.assertFalse(list(self.app.exception))
        self.assertEqual(self.app.session_state["matrix"][1][0]["delta"],0)

    def test_commodity_switch_isolates_sources(self):
        self.choose("Komoditas","ammonium_chloride")
        self.assertFalse(list(self.app.exception))
        self.assertEqual(self.app.session_state["freight_case"]["commodity"],"ammonium_chloride")
        self.assertTrue(any("tidak ditemukan" in c.value for c in self.app.caption))
        self.button("Hitung freight").click().run()
        self.assertFalse(list(self.app.exception))

    def test_matrix_updates_when_class_or_ports_change(self):
        self.button("Hitung freight").click().run()
        initial_key = self.app.session_state["matrix"][0]
        next(x for x in self.app.selectbox if x.label == "Kelas matrix").set_value("Supramax").run()
        self.assertFalse(list(self.app.exception))
        class_key, cells = self.app.session_state["matrix"]
        self.assertNotEqual(initial_key, class_key)
        self.assertEqual(cells[0]["scenario"]["vessel_class"], "Supramax")
        next(x for x in self.app.multiselect if x.label == "Port muat").set_value(
            [("Bontang", "Indonesia"), ("Kerteh", "Malaysia")]).run()
        self.assertFalse(list(self.app.exception))
        self.assertEqual(len(self.app.session_state["matrix"][1]), 2)

    def test_terms_changes_result_and_stales_old_output(self):
        self.button("Hitung freight").click().run()
        before=self.app.session_state["freight_result"]["classes"]["Handysize"]["nominal"]["days"]
        self.choose("Terms","SHEX0")
        self.assertTrue(any("Input berubah" in c.value for c in self.app.caption))
        self.button("Hitung freight").click().run()
        after=self.app.session_state["freight_result"]["classes"]["Handysize"]["nominal"]["days"]
        self.assertGreater(after,before)

    def test_calendar_and_oversized_cargo(self):
        self.choose("Basis waktu","calendar")
        self.assertFalse(list(self.app.exception))
        case=self.app.session_state["freight_case"]
        case["cargo_mt"]="999999"
        self.app.run()
        self.button("Hitung freight").click().run()
        self.assertFalse(list(self.app.exception))
        self.assertEqual(self.app.session_state["freight_result"]["recommendation"]["status"],"REVISE")

    def test_manual_fuel_and_hire_survive_refresh(self):
        case=self.app.session_state["freight_case"]
        override(case,"fuel.VLSFO.value","777")
        override(case,"profiles.Handysize.hire_usd_day","14000")
        self.market["bunkers"]["fo_price_usd_mt"]["value"]="999"
        self.app.run()
        self.assertEqual(self.app.session_state["freight_case"]["fuel"]["VLSFO"]["value"],"777")
        self.assertEqual(self.app.session_state["freight_case"]["profiles"]["Handysize"]["hire_usd_day"],"14000")

    def test_low_quote_deficit_and_tce_visible(self):
        self.app.session_state["freight_case"]["selling_freight_usd_mt"]="1"
        self.app.run()
        self.button("Hitung freight").click().run()
        self.assertFalse(list(self.app.exception))
        self.assertIn("TCE hasil USD/hari",[x.label for x in self.app.metric])
        self.assertEqual(self.app.session_state["freight_result"]["recommendation"]["status"],"REPRICE")

    def test_route_updates_distance_immediately(self):
        old=self.app.session_state["freight_case"]["distance_nm"]
        self.choose("Pelabuhan",("Aqaba","Jordan"),0)
        self.assertFalse(list(self.app.exception))
        case=self.app.session_state["freight_case"]
        self.assertEqual(case["ports"]["load"]["name"],"Aqaba")
        self.assertNotEqual(case["distance_nm"],old)

    def test_route_change_replaces_manual_distance_and_hides_old_result(self):
        case = self.app.session_state["freight_case"]
        key = case["case_id"] + "_0_shipment_route_0"
        self.app.session_state[key] = {"edited_rows": {3: {"Nilai": 3064.32}},
                                       "added_rows": [], "deleted_rows": []}
        self.app.run()
        self.assertEqual(float(self.app.session_state["freight_case"]["distance_nm"]), 3064.32)
        self.button("Hitung freight").click().run()
        self.choose("Pelabuhan", ("Kerteh", "Malaysia"), 0)
        self.assertTrue(any("Input berubah" in c.value for c in self.app.caption))
        self.choose("Pelabuhan", ("Hai Phong", "Vietnam"), 1)
        case = self.app.session_state["freight_case"]
        self.assertAlmostEqual(float(case["distance_nm"]), 1197.5913868621703)
        self.button("Hitung freight").click().run()
        result = self.app.session_state["freight_result"]
        self.assertEqual(result["case"]["distance_nm"], case["distance_nm"])
        self.assertTrue(any("Kerteh" in c.value and "Hai Phong" in c.value for c in self.app.caption))

    def test_port_change_clears_old_draft_editor_state(self):
        from pilog_cfr_dss.application.freight_desk import digest
        case = self.app.session_state["freight_case"]
        port = case["ports"]["discharge"]
        port_id = digest((port["name"], port["country"]))[:12]
        key = f"{case['case_id']}_0_discharge_{port_id}"
        self.app.session_state[key] = {"edited_rows": {2: {"Nilai": 9.2}},
                                       "added_rows": [], "deleted_rows": []}
        self.app.run()
        self.assertEqual(float(case["ports"]["discharge"]["draft_limit_m"]), 9.2)
        self.choose("Pelabuhan", ("Haldia", "India"), 1)
        self.assertIsNone(case["ports"]["discharge"]["draft_limit_m"])

    def test_route_failure_clears_previous_distance(self):
        with patch("pilog_cfr_dss.application.freight_desk.distance", side_effect=ValueError("offline")):
            self.choose("Pelabuhan", ("Kerteh", "Malaysia"), 0)
        case = self.app.session_state["freight_case"]
        self.assertIsNone(case["distance_nm"])
        self.assertEqual(case["sources"]["distance_nm"]["status"], "unavailable")
        self.button("Hitung freight").click().run()
        self.assertTrue(list(self.app.error))

    def test_new_case_resets_result(self):
        self.button("Hitung freight").click().run()
        self.button("Kasus baru").click().run()
        self.assertFalse(list(self.app.exception))
        with self.assertRaises(KeyError):
            self.app.session_state["freight_result"]

    def test_import_widget_epoch_preserves_imported_inputs(self):
        imported=deepcopy(self.app.session_state["freight_case"])
        imported["commodity"]="ammonium_chloride"
        imported["selling_freight_usd_mt"]="1"
        imported["ports"]["load"]["terms"]="SHEX0"
        imported["other_costs"] = [{"id": "cleaning", "label": "Pembersihan palka",
                                    "amount": "2500.15", "unit": "USD"}]
        self.app.session_state["freight_case"]=imported
        self.app.session_state["widget_generation"]=1
        self.app.session_state["replay_case"]=True
        with patch("pilog_cfr_dss.ui.views.fetch_online_inputs", side_effect=AssertionError("replay tried to fetch")):
            self.app.run()
        self.assertFalse(list(self.app.exception))
        current=self.app.session_state["freight_case"]
        self.assertEqual(current["commodity"],"ammonium_chloride")
        self.assertEqual(current["ports"]["load"]["terms"],"SHEX0")
        self.assertEqual(current["selling_freight_usd_mt"],"1")
        self.assertEqual(current["other_costs"], imported["other_costs"])
        self.button("Hitung freight").click().run()
        result = self.app.session_state["freight_result"]
        self.assertEqual(str(result["classes"]["Handysize"]["nominal"]["other_usd"]), "2500.15")
