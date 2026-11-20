from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal as D, localcontext
import unittest
from pilog_cfr_dss.calculations.capacity import bulk_capacity
from pilog_cfr_dss.calculations.freight_desk import calculate, quantities
from pilog_cfr_dss.calculations.port_time import port_duration, working_windows
from pilog_cfr_dss.models.freight_desk import TERMS, SCHEMA, FORMULA, TERMS_VERSION
import json


def example():
    profile = dict(dwt_mt="38200", grain_m3="47125", summer_draft_m="10.538", tpc_mt_cm="49",
        speed_knots="12", sea_vlsfo_mt_day="18", sea_lsmgo_mt_day="0.1", hire_usd_day="13000",
        port_vlsfo_mt_day="0", port_lsmgo_mt_day="2", bunkers_allowance_mt="1700", constants_allowance_mt="500")
    port = dict(name="A", country="X", rate_mt_day="5000", terms="SHINC", time_basis="factor",
        draft_limit_m=None, port_da_usd="100000", waiting_days="0", allowance_days="0", time_margin_percent="0",
        calendar={"timezone": "UTC", "holidays": []})
    discharge = deepcopy(port)
    discharge.update(name="B", country="Y")
    return dict(schema=SCHEMA, formula_version=FORMULA, terms_version=TERMS_VERSION,
        terms_snapshot=json.loads(json.dumps(TERMS)), currency="USD", sf_unit="m3/MT", commodity="urea_granular",
        cargo_mt="30000", stowage_factor_m3_mt="1.315", tolerance_percent="10",
        commission_fraction="0", hire_usd_day="13000", distance_nm="4320",
        start_at="2026-11-09T00:00:00+00:00", bunker_delay_days="0",
        ports={"load": port, "discharge": discharge}, selling_freight_usd_mt=None, other_costs=[],
        fuel={"VLSFO": {"value": "500"}, "LSMGO": {"value": "800"}},
        profiles={"Handysize": profile, "Supramax": deepcopy(profile)})


class FreightEngineTests(unittest.TestCase):
    def setUp(self):
        ctx = localcontext()
        ctx.__enter__().prec = 40
        self.addCleanup(ctx.__exit__, None, None, None)
        self.case = example()

    def nominal(self, case=None):
        return calculate(case or self.case)["classes"]["Handysize"]["nominal"]

    def test_port_margins_change_days_hire_and_bunker_once(self):
        self.case.update(cargo_mt="24000", tolerance_percent="0")
        load, discharge = self.case["ports"]["load"], self.case["ports"]["discharge"]
        load.update(rate_mt_day="4000", time_margin_percent="24.3", waiting_days="1", allowance_days="0.5")
        discharge.update(rate_mt_day="6000", time_margin_percent="24.3")
        row = self.nominal()
        self.assertEqual(row["port_times"]["load"]["operation_days"], D("7.458"))
        self.assertEqual(row["port_times"]["discharge"]["operation_days"], D("4.972"))
        self.assertEqual(row["days"], D("15") + D("7.458") + D("4.972") + D("1.5"))
        self.assertEqual(row["hire_usd"], row["days"] * D("13000"))
        port_fuel = sum(x["lsmgo_mt"] for x in row["ledger"] if x["activity"] != "Laut bermuatan")
        self.assertEqual(port_fuel, (D("7.458") + D("4.972") + D("1.5")) * D("2"))

    def test_calendar_margin_is_applied_after_calendar_once(self):
        self.case.update(cargo_mt="24000", tolerance_percent="0")
        port = self.case["ports"]["load"]
        port.update(rate_mt_day="4000", time_basis="calendar", time_margin_percent="25")
        row = self.nominal()
        self.assertEqual(row["port_times"]["load"]["terms_days"], D("6"))
        self.assertEqual(row["port_times"]["load"]["operation_days"], D("7.5"))

    def test_margin_missing_and_negative_are_rejected(self):
        port = self.case["ports"]["load"]
        for value in (None, "-1", "NaN"):
            port["time_margin_percent"] = value
            with self.assertRaises((ValueError, TypeError)):
                calculate(self.case)

    def test_independent_cost_reconciliation(self):
        row = self.nominal()
        # 4320/12/24=15 sea days; 30000/5000=6 days at each port.
        days = D(15) + D(6) + D(6)
        fuel = D(15)*D(18)*D(500) + (D(15)*D(".1")+D(12)*D(2))*D(800)
        expenses = fuel + D(200000)
        total = expenses + days*D(13000)
        self.assertEqual(row["days"], days)
        self.assertEqual(row["total_usd"], total)
        self.assertEqual(row["freight_usd_mt"], total/D(30000))
        self.assertEqual(sum(x["total_usd"] for x in row["ledger"]), total)
        self.assertIsNone(row["commercial"])

    def test_quote_deficit_and_tce_before_hire(self):
        self.case["selling_freight_usd_mt"] = "1"
        row = self.nominal()
        self.assertLess(row["commercial"]["surplus_usd"], 0)
        self.assertEqual(row["commercial"]["tce_usd_day"],
            (D(30000)-row["voyage_expenses_usd"])/row["days"])
        self.assertGreaterEqual(row["minimum_offer_usd_mt"]*D(30000), row["total_usd"])

    def test_independent_selling_quote_can_make_real_surplus(self):
        self.case["selling_freight_usd_mt"]="30"
        row=self.nominal()
        self.assertEqual(row["commercial"]["net_freight_revenue_usd"],D(900000))
        self.assertGreater(row["commercial"]["surplus_usd"],0)
        self.assertEqual(row["commercial"]["surplus_usd"],
                         D(900000)-row["voyage_expenses_usd"]-row["hire_usd"])

    def test_quantity_scenarios_recalculate_time_and_cost(self):
        rows = calculate(self.case)["classes"]["Handysize"]
        self.assertEqual([rows[k]["cargo_mt"] for k in rows], [D(27000), D(30000), D(33000)])
        self.assertLess(rows["minimum"]["days"], rows["nominal"]["days"])
        self.assertLess(rows["nominal"]["total_usd"], rows["maximum"]["total_usd"])
        self.case["tolerance_percent"] = "0"
        rows = calculate(self.case)["classes"]["Handysize"]
        self.assertEqual(rows["minimum"], rows["maximum"])

    def test_volume_binding_and_upper_tolerance_fail(self):
        self.case["profiles"]["Handysize"]["grain_m3"] = "40000"
        rows = calculate(self.case)["classes"]["Handysize"]
        self.assertTrue(rows["nominal"]["feasible"])
        self.assertFalse(rows["maximum"]["feasible"])
        self.assertEqual(rows["maximum"]["capacity"]["binding"], "VOLUME")

    def test_sf_changes_capacity_not_price_when_nonbinding(self):
        original = self.nominal()
        self.case["stowage_factor_m3_mt"] = "1"
        self.assertEqual(self.nominal()["freight_usd_mt"], original["freight_usd_mt"])
        self.case["stowage_factor_m3_mt"] = "10"
        self.assertFalse(self.nominal()["feasible"])

    def test_draft_lower_cap_no_increase_for_deep_port(self):
        profile = self.case["profiles"]["Handysize"]
        a = bulk_capacity(profile, D(30000), D(1), [D(30), D(30)])
        b = bulk_capacity(profile, D(30000), D(1), [D("10"), D(30)])
        self.assertEqual(a["limit_mt"], D(36000))
        self.assertEqual(b["limit_mt"], D(36000)-(D("10.538")-D(10))*D(100)*D(49))
        self.assertEqual(a["checks"][2]["status"], "ESTIMATED_PASS")
        self.assertEqual(bulk_capacity(profile,D(30000),D(1),[None,None])["checks"][2]["status"], "NOT_MODELLED")

    def test_exact_weight_boundary_and_allowance(self):
        self.case["cargo_mt"] = "36000"
        self.case["stowage_factor_m3_mt"] = "1"
        self.assertTrue(self.nominal()["feasible"])
        self.case["cargo_mt"] = "36000.01"
        self.assertFalse(self.nominal()["feasible"])

    def test_port_terms_add_hire_and_bunker_once(self):
        base = self.nominal()
        self.case["ports"]["load"]["terms"] = "SHEX0"
        changed = self.nominal()
        delta = D(6)*(D("1.1667")-1)
        self.assertEqual(changed["days"]-base["days"], delta)
        self.assertEqual(changed["total_usd"]-base["total_usd"], delta*(D(13000)+D(2)*D(800)))

    def test_identical_factor_terms_are_equivalent(self):
        base = self.nominal()
        for code in ("CQD1", "FHINC", "SHINC"):
            self.case["ports"]["load"]["terms"] = code
            self.assertEqual(self.nominal()["total_usd"], base["total_usd"])

    def test_thex3_changes_only_selected_port_time_and_cost(self):
        base = self.nominal()
        self.case["ports"]["load"]["terms"] = "THEX3"
        changed = self.nominal()
        additional = (D(30000) / D(5000)) * (D("1.35") - 1)
        self.assertEqual(changed["days"] - base["days"], additional)
        self.assertEqual(changed["total_usd"] - base["total_usd"],
                         additional * (D(13000) + D(2) * D(800)))
        old_discharge = next(x for x in base["ledger"] if x["activity"] == "Bongkar")
        new_discharge = next(x for x in changed["ledger"] if x["activity"] == "Bongkar")
        self.assertEqual(old_discharge, new_discharge)

    def test_other_cost_id_and_unit_and_delay(self):
        base = self.nominal()
        self.case["other_costs"] = [{"id":"clean","label":"Cleaning","amount":"2500","unit":"USD"}]
        self.assertEqual(self.nominal()["total_usd"]-base["total_usd"], D(2500))
        self.case["other_costs"].append(deepcopy(self.case["other_costs"][0]))
        self.assertEqual(self.nominal()["status"], "INPUT_ERROR")
        self.case["other_costs"] = [{"id":"clean","amount":"1","unit":"USD/MT"}]
        self.assertEqual(self.nominal()["status"], "INPUT_ERROR")
        self.case["other_costs"] = []
        self.case["bunker_delay_days"] = "1.5"
        self.assertEqual(self.nominal()["days"]-base["days"], D("1.5"))

    def test_invalid_global_inputs(self):
        for key, value in [("cargo_mt","0"),("cargo_mt","NaN"),("tolerance_percent","100"),
            ("tolerance_percent","-1"),("currency","EUR"),("sf_unit","MT/m3"),
            ("distance_nm","-2"),("commission_fraction","0.1"),("schema","PILOG-CASE.2")]:
            with self.subTest(key=key, value=value):
                case=deepcopy(self.case);case[key]=value
                with self.assertRaises(ValueError): calculate(case)

    def test_class_error_does_not_block_other_class(self):
        self.case["profiles"]["Handysize"]["speed_knots"]="0"
        rows=calculate(self.case)["classes"]
        self.assertEqual(rows["Handysize"]["nominal"]["status"],"INPUT_ERROR")
        self.assertTrue(rows["Supramax"]["nominal"]["feasible"])

    def test_small_cargo_full_voyage_cost_not_invented_profit(self):
        self.case["cargo_mt"]="30"
        row=self.nominal()
        self.assertGreater(row["freight_usd_mt"], D(1000))
        self.assertIsNone(row["commercial"])

    def test_input_immutable(self):
        old=deepcopy(self.case);calculate(self.case);self.assertEqual(self.case,old)

    def test_cost_change_holds_independent_quote_fixed(self):
        self.case["selling_freight_usd_mt"]="30"
        base=self.nominal()
        self.case["fuel"]["VLSFO"]["value"]="700"
        changed=self.nominal()
        self.assertEqual(changed["commercial"]["selling_freight_usd_mt"],D(30))
        self.assertEqual(changed["commercial"]["net_freight_revenue_usd"],base["commercial"]["net_freight_revenue_usd"])
        self.assertLess(changed["commercial"]["surplus_usd"],base["commercial"]["surplus_usd"])


class PortCalendarTests(unittest.TestCase):
    def port(self, term):
        return dict(rate_mt_day="1000",terms=term,time_basis="calendar",calendar={"timezone":"UTC","holidays":[]})

    def test_all_23_factor_values_used(self):
        self.assertEqual(len(TERMS),23)
        start=datetime(2026,11,9,tzinfo=timezone.utc)
        for code,item in TERMS.items():
            p=self.port(code);p["time_basis"]="factor"
            self.assertEqual(port_duration(D(1000),p,start)[0],D(item["factor"]))

    def test_weekend_crossing_no_factor_double_count(self):
        p=self.port("SHEX1")
        start=datetime(2026,11,7,0,tzinfo=timezone.utc)  # Saturday
        days,end=port_duration(D(1000),p,start)
        self.assertEqual(days,D("2.5"))
        self.assertEqual(end.isoformat(),"2026-11-09T12:00:00+00:00")

    def test_monday_wrapped_exclusion(self):
        self.assertEqual(working_windows("SHEX2",0),[(480,1440)])
        self.assertEqual(working_windows("SHEX2",6),[])
        self.assertEqual(working_windows("SHEX2",5),[(0,720)])

    def test_thex3_calendar_excludes_thursday_noon_to_saturday_morning(self):
        self.assertEqual(working_windows("THEX3",3),[(0,720)])
        self.assertEqual(working_windows("THEX3",4),[])
        self.assertEqual(working_windows("THEX3",5),[(480,1440)])
        days,end=port_duration(D(1000),self.port("THEX3"),datetime(2026,11,12,12,tzinfo=timezone.utc))
        self.assertEqual(end.isoformat(),"2026-11-15T08:00:00+00:00")
        self.assertEqual(days,D(68)/D(24))

    def test_holiday_and_timezone(self):
        p=self.port("SHINC")
        p["calendar"]={"timezone":"Asia/Jakarta","holidays":["2026-11-09"]}
        days,end=port_duration(D(1000),p,datetime.fromisoformat("2026-11-09T00:00:00+07:00"))
        self.assertEqual(days,D(2))
        self.assertEqual(end.astimezone(timezone.utc).isoformat(),"2026-11-10T17:00:00+00:00")

    def test_empty_calendar_has_finite_horizon(self):
        p=self.port("SHINC");p["calendar"]["windows"]={str(i):[] for i in range(7)}
        with self.assertRaisesRegex(ValueError,"HORIZON"):port_duration(D(1000),p,datetime(2026,11,9,tzinfo=timezone.utc))

    def test_invalid_windows_and_timezone(self):
        for calendar in ({"timezone":"Not/AZone"}, {"timezone":"UTC","windows":{"0":[[100,200],[150,300]]}}):
            p=self.port("SHINC");p["calendar"]=calendar
            with self.assertRaises(ValueError): port_duration(D(1000),p,datetime(2026,11,9,tzinfo=timezone.utc))
