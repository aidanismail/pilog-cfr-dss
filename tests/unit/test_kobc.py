from copy import deepcopy
from datetime import date
from pathlib import Path
from tempfile import gettempdir
import unittest
from uuid import uuid4
from pilog_cfr_dss.sources.kobc import URLS, parse_table, remember_snapshot, select_assessment
from pilog_cfr_dss.application.freight_desk import sync_kobc


def quote(family, observed="2026-11-19"):
    values = {"MH3": "17000", "TC Average": "16000"} if family == "Handysize" else {"MS5": "20000", "MS6": "21000", "TC Average": "22000"}
    return {"unit": "USD/day", "observed_on": observed, "values": values,
            "source_url": "https://www.kobc.or.kr/", "fetched_at": "2026-11-20T00:00:00Z",
            "benchmark_dwt_mt": 33000 if family == "Handysize" else 58000,
            "commission_basis": "5%"}


class KobcTests(unittest.TestCase):
    def test_partial_outage_keeps_last_quote_with_its_original_date(self):
        folder = Path(gettempdir()) / ("pilog_kobc_test_" + uuid4().hex)
        folder.mkdir()
        self.addCleanup(folder.rmdir)
        self.addCleanup((folder / "kobc_latest.json").unlink, missing_ok=True)
        source = {family: dict(quote(family), source_url=URLS[family]) for family in URLS}
        remember_snapshot({"classes": source, "errors": {}}, folder)
        incoming = {"classes": {"Supramax": dict(source["Supramax"], observed_on="2026-11-20")},
                    "errors": {"Handysize": "offline"}}
        refreshed = remember_snapshot(incoming, folder)
        self.assertEqual(refreshed["classes"]["Handysize"], source["Handysize"])
        self.assertEqual(refreshed["classes"]["Supramax"]["observed_on"], "2026-11-20")
        load = {"name": "Bontang", "country": "Indonesia"}
        discharge = {"name": "Mundra", "country": "India"}
        self.assertIsNone(select_assessment(refreshed, "Handysize", load, discharge, date(2026, 11, 27)))

    def test_parse_realistic_table_and_freshness(self):
        html = "<table><tr><th>Date</th><th>MH1</th><th>MH2</th><th>MH3</th><th>MH4</th><th>MH5</th><th>TC Average</th></tr>" \
               "<tr><td>2026-11-19</td><td>17,410</td><td>14,326</td><td>15,821</td><td>15,960</td><td>18,247</td><td>16,353</td></tr></table>"
        result = parse_table(html, "Handysize", date(2026, 11, 20))
        self.assertEqual(result["values"]["TC Average"], "16353")
        self.assertEqual(result["observed_on"], "2026-11-19")
        with self.assertRaisesRegex(ValueError, "FRESH"):
            parse_table(html, "Handysize", date(2026, 11, 27))
        with self.assertRaisesRegex(ValueError, "HEADER"):
            parse_table(html.replace("TC Average", "Unknown"), "Handysize", date(2026, 11, 20))

    def test_route_match_then_class_fallback_and_boundary(self):
        snap = {"classes": {"Supramax": quote("Supramax")}}
        origin = {"name": "Bontang", "country": "Indonesia"}
        haldia = {"name": "Haldia", "country": "India"}
        mundra = {"name": "Mundra", "country": "India"}
        self.assertEqual(select_assessment(snap, "Supramax", origin, haldia, date(2026, 11, 26))["code"], "MS5")
        self.assertEqual(select_assessment(snap, "Supramax", origin, mundra, date(2026, 11, 20))["code"], "TC Average")
        self.assertIsNone(select_assessment(snap, "Supramax", origin, haldia, date(2026, 11, 27)))
        snap["classes"]["Handysize"] = quote("Handysize")
        self.assertEqual(select_assessment(snap, "Handysize", origin, {"name": "Qingdao", "country": "China"}, date(2026, 11, 20))["code"], "MH3")
        self.assertEqual(select_assessment(snap, "Supramax", origin, {"name": "Ningbo", "country": "China"}, date(2026, 11, 20))["code"], "MS6")

    def test_sync_keeps_manual_quote_and_expires_auto(self):
        case = {"profiles": {"Handysize": {"hire_usd_day": "13000"}, "Supramax": {"hire_usd_day": "14000"}},
                "sources": {"profiles.Supramax.hire_usd_day": {"status": "manual_override"}},
                "ports": {"load": {"name": "Bontang", "country": "Indonesia"},
                          "discharge": {"name": "Mundra", "country": "India"}}}
        incoming = {"classes": {f: quote(f) for f in ("Handysize", "Supramax")}, "errors": {}}
        self.assertTrue(sync_kobc(case, incoming, date(2026, 11, 20)))
        self.assertEqual(case["profiles"]["Handysize"]["hire_usd_day"], "16000")
        self.assertEqual(case["profiles"]["Supramax"]["hire_usd_day"], "14000")
        sync_kobc(case, {"classes": {}, "errors": {"Handysize": "offline"}}, date(2026, 11, 27))
        self.assertIsNone(case["profiles"]["Handysize"]["hire_usd_day"])
        self.assertEqual(case["profiles"]["Supramax"]["hire_usd_day"], "14000")
