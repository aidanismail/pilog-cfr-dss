from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from pilog_cfr_dss.sources.fearnpulse import normalize_payloads, _request
from pilog_cfr_dss.sources.voyage_profiles import read_profiles
from pilog_cfr_dss.models.tender_clock import round_window, bid_in_round
from pilog_cfr_dss.decisions.iteration_04 import evaluate_tender
from pilog_cfr_dss.calculations.tender_04 import bid_prices
from pilog_cfr_dss.reporting.formatting import price_time
from decimal import Decimal as D

ROOT = Path(__file__).resolve().parents[2]


def sample_payloads():
    return {
        "fearnpulse_report.json": json.dumps({"data": {"report": [{"id": "test-report", "created_at": "2026-10-21T12:00:00+00:00"}]}}),
        "fearnpulse_tc.json": json.dumps({"data": {"rate_meta": [
            {"info": {"route": "Handysize (38 000 dwt)", "rate_type": "BULK", "rate_subtype": "TC"},
             "rates": [{"date": "2026-10-21", "rate": 14500}, {"date": "2026-10-14", "rate": 15500}]},
            {"info": {"route": "Supramax (58 000 dwt)", "rate_type": "BULK", "rate_subtype": "TC"},
             "rates": [{"date": "2026-10-21", "rate": 17500}]}]}}),
        **{f"fearnpulse_{key}.json": json.dumps({"columns": ["tsid", "value", "date", "jobid"],
            "data": [[key, rate, 1782864000000, 15]]}) for key, rate in ((306, 458), (307, 902))},
    }


class MarketParserTests(unittest.TestCase):
    def normalize(self, raw=None):
        return normalize_payloads(raw or sample_payloads(), "2026-10-27T02:00:00+00:00")

    def test_actual_value_unit_date_and_fetch_are_distinct(self):
        s = self.normalize()
        self.assertEqual(s["tc_rates"]["Handysize"]["value"], "14500")
        self.assertEqual(s["tc_rates"]["Supramax"]["unit"], "USD/day")
        self.assertEqual(s["bunkers"]["fo_price_usd_mt"]["source_observed_on"], "2026-07-01")
        self.assertEqual(s["tc_rates"]["Handysize"]["source_observed_on"], "2026-10-21")
        self.assertNotEqual(s["fetched_at"], s["report_published_at"])
        self.assertEqual(s["tc_rates"]["Handysize"]["commission_basis"], "not_stated_by_source")

    def test_missing_required_class_does_not_fall_back(self):
        raw = sample_payloads(); data = json.loads(raw["fearnpulse_tc.json"])
        data["data"]["rate_meta"].pop()
        raw["fearnpulse_tc.json"] = json.dumps(data)
        with self.assertRaisesRegex(ValueError, "MISSING_REQUIRED_CLASS"):
            self.normalize(raw)

    def test_zero_negative_and_nonfinite_rates_rejected(self):
        for value in (0, -1, "NaN", "Infinity"):
            with self.subTest(value=value):
                raw = sample_payloads(); data = json.loads(raw["fearnpulse_tc.json"])
                data["data"]["rate_meta"][0]["rates"][0]["rate"] = value
                raw["fearnpulse_tc.json"] = json.dumps(data)
                with self.assertRaises(ValueError):
                    self.normalize(raw)

    def test_graphql_errors_and_changed_ts_schema_rejected(self):
        for key, value in (("fearnpulse_tc.json", {"errors": [{"message": "schema changed"}]}),
                           ("fearnpulse_306.json", {"columns": ["wrong"], "data": []})):
            raw = sample_payloads(); raw[key] = json.dumps(value)
            with self.assertRaises(ValueError):
                self.normalize(raw)

    def test_duplicate_class_and_future_observation_rejected(self):
        for duplicate in (True, False):
            raw = sample_payloads(); data = json.loads(raw["fearnpulse_tc.json"])
            if duplicate:
                data["data"]["rate_meta"].append(deepcopy(data["data"]["rate_meta"][0]))
            else:
                data["data"]["rate_meta"][0]["rates"][0]["date"] = "2026-10-28"
            raw["fearnpulse_tc.json"] = json.dumps(data)
            with self.assertRaisesRegex(ValueError, "AMBIGUOUS_TC"):
                self.normalize(raw)

    def test_column_mapping_not_positional_guess(self):
        raw = sample_payloads()
        raw["fearnpulse_306.json"] = json.dumps({"columns": ["date", "value", "tsid"], "data": [[1782864000000, 458, 306]]})
        self.assertEqual(self.normalize(raw)["bunkers"]["fo_price_usd_mt"]["value"], "458")

    def test_exact_decimal_not_binary_float_round_trip(self):
        raw = sample_payloads()
        raw["fearnpulse_306.json"] = '{"columns":["tsid","value","date"],"data":[[306,458.1234567890123456789,1782864000000]]}'
        self.assertEqual(self.normalize(raw)["bunkers"]["fo_price_usd_mt"]["value"], "458.1234567890123456789")

    def test_network_failure_has_bounded_retry_and_no_quote(self):
        with patch("pilog_cfr_dss.sources.fearnpulse.urlopen", side_effect=OSError("offline")) as request:
            with self.assertRaisesRegex(OSError, "offline"):
                _request("https://fearnpulse.com/")
        self.assertEqual(request.call_count, 2)


class WorkbookProfilesTests(unittest.TestCase):
    def test_all_four_profiles_classified_and_laden_inputs_mapped(self):
        result = read_profiles(ROOT / "data/raw/Voyage Estimate.xlsx")
        profiles = {p["sheet"]: p for p in result["profiles"]}
        self.assertEqual(set(profiles), {"Bontang-Mundra", "Bontang-Davao", "Bontang-Bangkok", "Bontang-Hai Phong"})
        self.assertEqual(profiles["Bontang-Mundra"]["fields"]["dwt_mt"], "36000")
        self.assertEqual(profiles["Bontang-Davao"]["fields"]["speed_knots"], "12.5")
        self.assertEqual(profiles["Bontang-Bangkok"]["fields"]["speed_knots"], "12")
        self.assertEqual(profiles["Bontang-Hai Phong"]["vessel_class"], "Supramax")
        self.assertFalse(any(p["market_class_proxy"] for p in profiles.values()))
        self.assertEqual(D(profiles["Bontang-Mundra"]["fields"]["port_do_mt_day"]), D("2.52"))
        self.assertTrue(all(D(p["fields"]["dwt_mt"]) <= 60000 for p in profiles.values()))
        self.assertNotIn("baltic", json.dumps(result).lower())

    def test_two_handysize_two_supramax_have_distinct_physical_assumptions(self):
        from collections import Counter
        result = read_profiles(ROOT / "data/raw/Voyage Estimate.xlsx")
        profiles = result["profiles"]
        self.assertEqual(Counter(p["vessel_class"] for p in profiles), {"Handysize":2,"Supramax":2})
        self.assertEqual({p["fields"]["dwt_mt"] for p in profiles},{"36000","38000","54000","58000"})
        for key in ("speed_knots","sea_fo_mt_day","sea_do_mt_day","port_do_mt_day","running_usd_day"):
            self.assertEqual(len({p["fields"][key] for p in profiles}),4,key)
        self.assertTrue(all(p["source_status"] == "simulation_only_workbook_vessel_profile" for p in profiles))
        self.assertTrue(all("sintetis" in p["note"] for p in profiles))
        self.assertEqual({p["profile_id"] for p in profiles},{"ve_sheet1","ve_aqaba","ve_sby","ve_godau"})
        self.assertEqual([p["market_family"] for p in profiles],["Handysize","Handysize","Supramax","Supramax"])

    def test_historical_handymax_profile_remains_readable_without_reclassifying_it(self):
        result = read_profiles(ROOT / "docs/it_4/Voyage Estimate I4.xlsx")
        handymax = next(p for p in result["profiles"] if p["sheet"]=="Godau")
        self.assertEqual(handymax["vessel_class"],"Handymax")
        self.assertTrue(handymax["market_class_proxy"])


class FixedRoundTests(unittest.TestCase):
    clock = {"mode": "fixed_window", "round_duration_seconds": 180, "starts_at": "2026-10-27T02:00:00+00:00"}

    def test_open_inclusive_close_exclusive(self):
        self.assertTrue(bid_in_round({"round": 1, "submitted_at": "2026-10-27T02:00:00+00:00"}, self.clock))
        self.assertTrue(bid_in_round({"round": 1, "submitted_at": "2026-10-27T02:02:59+00:00"}, self.clock))
        self.assertFalse(bid_in_round({"round": 1, "submitted_at": "2026-10-27T02:03:00+00:00"}, self.clock))
        self.assertFalse(bid_in_round({"round": 1, "submitted_at": "2026-10-27T01:59:59+00:00"}, self.clock))

    def test_round_four_is_supported_without_resetting_clock(self):
        start, end = round_window(self.clock, 4)
        self.assertEqual(start.isoformat(), "2026-10-27T02:09:00+00:00")
        self.assertEqual(end.isoformat(), "2026-10-27T02:12:00+00:00")

    def test_late_bid_cannot_displace_valid_last_bid(self):
        bids = [{"bid_id": "valid", "buyer_id": "A", "round": 1, "sequence": 1, "alpha_usd_mt": "10", "status": "active", "submitted_at": "2026-10-27T02:01:00+00:00"},
                {"bid_id": "late", "buyer_id": "A", "round": 1, "sequence": 2, "alpha_usd_mt": "100", "status": "active", "submitted_at": "2026-10-27T02:03:01+00:00"}]
        result = evaluate_tender(bid_prices(D(415), D(420), D(25), bids), {"auction_clock": self.clock, "evaluation_cutoff": "2026-10-27T02:10:00+00:00"})
        self.assertEqual(result["candidate_bid_ids"], ["valid"])
        self.assertIn("3 menit", result["bids"][1]["reason"])

    def test_invalid_clock_cannot_silently_extend_round(self):
        with self.assertRaisesRegex(ValueError, "INVALID_AUCTION_CLOCK"):
            round_window({**self.clock, "round_duration_seconds": 181}, 1)

    def test_scheduled_last_bid_follows_received_time_not_edited_sequence(self):
        bids = [{"bid_id": "later", "buyer_id": "A", "round": 1, "sequence": 1, "alpha_usd_mt": "10", "status": "active", "submitted_at": "2026-10-27T02:02:00+00:00"},
                {"bid_id": "earlier", "buyer_id": "A", "round": 1, "sequence": 2, "alpha_usd_mt": "100", "status": "active", "submitted_at": "2026-10-27T02:01:00+00:00"}]
        result = evaluate_tender(bid_prices(D(415), D(420), D(25), bids), {"auction_clock": self.clock, "evaluation_cutoff": "2026-10-27T02:03:00+00:00"})
        self.assertEqual(result["candidate_bid_ids"], ["later"])

    def test_timestamp_formatting_never_invents_unknown_or_date_only_time(self):
        self.assertEqual(price_time(None), "Tidak tersedia")
        self.assertEqual(price_time("2026-10-21"), "2026-10-21")
        self.assertIn("09:00:00 WIB", price_time("2026-10-27T02:00:00+00:00"))
