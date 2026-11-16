"""Freight Desk UI tests. Historical auction UI tests retired with tender scope."""
from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from pilog_cfr_dss.sources.fearnpulse import latest_saved
from pilog_cfr_dss.application.freight_desk import override

ROOT=Path(__file__).resolve().parents[2]


class FreightDeskUITests(unittest.TestCase):
    def setUp(self):
        self.market=latest_saved(ROOT)
        self.patcher=patch("pilog_cfr_dss.ui.views.fresh_market",return_value=self.market)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
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
        override(case,"hire_usd_day","14000")
        self.market["bunkers"]["fo_price_usd_mt"]["value"]="999"
        self.app.run()
        self.assertEqual(self.app.session_state["freight_case"]["fuel"]["VLSFO"]["value"],"777")
        self.assertEqual(self.app.session_state["freight_case"]["hire_usd_day"],"14000")

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
        self.app.session_state["freight_case"]=imported
        self.app.session_state["widget_generation"]=1
        self.app.session_state["replay_case"]=True
        self.app.run()
        current=self.app.session_state["freight_case"]
        self.assertEqual(current["commodity"],"ammonium_chloride")
        self.assertEqual(current["ports"]["load"]["terms"],"SHEX0")
        self.assertEqual(current["selling_freight_usd_mt"],"1")
