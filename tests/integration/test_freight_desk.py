from copy import deepcopy
from decimal import Decimal as D
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from pilog_cfr_dss.application.freight_desk import (
    default_case, evaluate, export_case, import_case, matrix, override, digest, select_terms)
from pilog_cfr_dss.calculations.freight_desk import calculate
from pilog_cfr_dss.sources.fearnpulse import latest_saved
from pilog_cfr_dss.sources.fertilizer_reports import read_assessments, for_product, _read, destination_context
from pilog_cfr_dss.reporting.commercial_brief import commercial_brief
from tests.unit.test_freight_desk import example
from pilog_cfr_dss.models.freight_desk import terms_catalog

ROOT=Path(__file__).resolve().parents[2]


class FreightIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case=default_case(ROOT,latest_saved(ROOT))

    def test_new_case_defaults_to_25_percent_for_each_port(self):
        for side in ("load", "discharge"):
            self.assertEqual(self.case["ports"][side]["time_margin_percent"], "25")

    def test_sources_for_three_products_and_no_fabricated_fertecon_chloride(self):
        snapshot=read_assessments(ROOT)
        self.assertFalse(snapshot["errors"])
        for product in ("urea_granular","ammonium_sulphate","ammonium_chloride"):
            rows=for_product(snapshot,product)
            self.assertTrue(rows)
            self.assertTrue(all(r["product"]==product and r["unit"]=="USD/MT" for r in rows))
        chloride=for_product(snapshot,"ammonium_chloride")
        self.assertEqual({r["publisher"] for r in chloride},{"Argus"})
        self.assertEqual((chloride[0]["low"],chloride[0]["high"]),("135","150"))
        self.assertEqual(chloride[0]["page"],2)
        self.assertEqual({r["publisher"] for r in for_product(snapshot,"ammonium_sulphate")},{"Argus","Fertecon"})

    def test_fertilizer_prices_do_not_change_cost_engine(self):
        c=deepcopy(self.case);base=calculate(c)
        for product in ("ammonium_chloride","ammonium_sulphate"):
            c["commodity"]=product
            self.assertEqual(calculate(c),base)

    def test_report_excludes_wrong_unit_grade(self):
        rows=read_assessments(ROOT)["records"]
        self.assertTrue(all("$/st" not in r["label"] for r in rows))
        urea=for_product(read_assessments(ROOT),"urea_granular")
        self.assertTrue(all("prilled" not in r["label"].lower() for r in urea))
        point=next(r for r in rows if r.get("symbol")=="SMEAA04")
        self.assertEqual((point["low"],point["high"]),("120.00","120.00"))

    def test_hash_cache_mismatch_not_accepted(self):
        p=next((ROOT/"public").glob("Argus*Nitrogen*.pdf"))
        with self.assertRaisesRegex(ValueError,"CHANGED"):_read(str(p.resolve()),"wrong")

    def test_destination_region_preserves_product_and_basis(self):
        snapshot=read_assessments(ROOT)
        sea=destination_context(snapshot,"urea_granular","Vietnam")
        self.assertTrue(all(row["basis"]=="CFR" for row in sea))
        libya=destination_context(snapshot,"urea_granular","Libya")
        self.assertTrue(all(row["basis"]=="FOB" and "North Africa" in row["label"] for row in libya))
        chloride=destination_context(snapshot,"ammonium_chloride","India")
        self.assertTrue(all(row["product"]=="ammonium_chloride" for row in chloride))
        self.assertTrue(all("bukan harga CFR tujuan" in row["context_scope"] for row in chloride))

    def test_package_exact_replay_and_tamper(self):
        original=calculate(self.case)
        restored=import_case(export_case(self.case))
        self.assertEqual(calculate(restored),original)
        payload=json.loads(export_case(self.case));payload["case"]["cargo_mt"]="1"
        with self.assertRaisesRegex(ValueError,"HASH"):import_case(json.dumps(payload).encode())
        with self.assertRaisesRegex(ValueError,"lama"):import_case(b'{"format":"PILOG-CASE.2"}')
        with self.assertRaises(ValueError):import_case(b'{"format":1,"format":2}')
        with self.assertRaises(ValueError):import_case(b'[]')
        with self.assertRaises(ValueError):import_case(b'null')
        changed=deepcopy(self.case)
        changed["terms_snapshot"]["SHINC"]["factor"]="1.2"
        with self.assertRaisesRegex(ValueError,"TERMS_VERSION"):calculate(changed)

    def test_old_packages_migrate_after_hash_and_preserve_calculation(self):
        for path in (ROOT / "outputs/contoh_6_kasus").glob("*.json"):
            raw = path.read_bytes()
            old = json.loads(raw)["case"]
            before = calculate(old)["classes"]
            migrated = import_case(raw)
            self.assertEqual(migrated["formula_version"], "FD.2")
            self.assertEqual(calculate(migrated)["classes"], before)
            self.assertEqual(migrated["ports"]["load"]["time_margin_percent"], "0")
            self.assertEqual(migrated["sources"]["formula_version"]["status"], "migrated")

    def test_override_preserves_source_and_original(self):
        c=deepcopy(self.case);old=digest(c)
        override(c,"hire_usd_day","14000")
        self.assertNotEqual(digest(c),old)
        self.assertEqual(c["sources"]["hire_usd_day"]["original"],"13000")
        self.assertEqual(c["sources"]["hire_usd_day"]["status"],"manual_override")

    def test_legacy_terms_replay_and_explicit_thex3_selection(self):
        c=deepcopy(self.case)
        c["terms_version"]="CMN-TERMS.1"
        c["terms_snapshot"]=json.loads(json.dumps(terms_catalog("CMN-TERMS.1")))
        old=digest(c)
        baseline=calculate(c)
        restored=import_case(export_case(c))
        self.assertEqual(digest(restored),old)
        self.assertEqual(calculate(restored),baseline)
        select_terms(restored,"load","THEX3")
        self.assertEqual(restored["terms_version"],"CMN-TERMS.2")
        self.assertIn("THEX3",restored["terms_snapshot"])
        self.assertGreater(calculate(restored)["classes"]["Handysize"]["nominal"]["days"],
                           baseline["classes"]["Handysize"]["nominal"]["days"])

    def test_brief_has_actions_five_sections_and_no_tender(self):
        result=evaluate(self.case);text=commercial_brief(result)
        for term in ("## 1.","## 2.","## 3.","## 4.","## 5.","Minimum penawaran","Belum dimodelkan","Fearnpulse terakhir diambil","SHA-256"):
            self.assertIn(term,text)
        self.assertEqual(text.count("\n## "),5)
        for term in ("OE/HPS","putaran bid","winner","Gate A"):
            self.assertNotIn(term,text)
        self.assertIn("belum dihitung",text)
        c=deepcopy(self.case);c["selling_freight_usd_mt"]="1"
        result=evaluate(c)
        self.assertEqual(result["recommendation"]["status"],"REPRICE")
        self.assertIn("Naikkan minimal",commercial_brief(result))

    def test_recommendation_upper_limit_all_fail_and_tie(self):
        c=example();c["profiles"]["Handysize"]["grain_m3"]="40000";c["profiles"]["Supramax"]["grain_m3"]="40000"
        from pilog_cfr_dss.decisions.freight_desk import recommend
        rec=recommend(calculate(c))
        self.assertIn("UPPER_TOLERANCE_NOT_FULLY_FEASIBLE",rec["reasons"])
        self.assertIn("EQUAL_COST_OPTIONS",rec["reasons"])
        c["cargo_mt"]="99999"
        self.assertEqual(recommend(calculate(c))["status"],"REVISE")

    def test_matrix_base_parity_manual_distance_no_mutation(self):
        c=deepcopy(self.case);c["distance_nm"]="4320";old=deepcopy(c)
        a=c["ports"]["load"];b=c["ports"]["discharge"]
        cells=matrix(c,[(a["name"],a["country"])],[(b["name"],b["country"])],"Handysize",ROOT)
        self.assertEqual(cells[0]["rate"],calculate(c)["classes"]["Handysize"]["nominal"]["freight_usd_mt"])
        self.assertEqual(cells[0]["delta"],0)
        self.assertEqual(c,old)

    def test_matrix_route_failure_not_zero_and_draft_not_inherited(self):
        c=deepcopy(self.case);c["ports"]["load"]["draft_limit_m"]="12"
        a=c["ports"]["load"];b=c["ports"]["discharge"]
        with patch("pilog_cfr_dss.application.freight_desk.distance",side_effect=ValueError("down")):
            cells=matrix(c,[(a["name"],a["country"])],[("Unknown","Nowhere")],"Handysize",ROOT)
        self.assertIsNone(cells[0]["rate"])
        self.assertTrue(cells[0]["error"])
        with self.assertRaises(ValueError):matrix(c,[("A","X")]*6,[("B","Y")]*5,"Handysize",ROOT)

    def test_matrix_new_port_parameters_used_and_base_frozen(self):
        c=deepcopy(self.case);old=deepcopy(c)
        a=c["ports"]["load"]
        fake={"value":"4320","unit":"NM","source_reference":"test route"}
        override_values={("discharge","C","Z"):{"port_da_usd":"1234","terms":"SHEX0","rate_mt_day":"6000", "time_margin_percent":"24.3"}}
        with patch("pilog_cfr_dss.application.freight_desk.distance",return_value=fake):
            cells=matrix(c,[(a["name"],a["country"])],[("C","Z")],"Handysize",ROOT,port_overrides=override_values)
        self.assertEqual(c,old)
        derived=cells[0]["result"]["case"]
        self.assertEqual(derived["ports"]["discharge"]["port_da_usd"],"1234")
        self.assertEqual(derived["ports"]["discharge"]["terms"],"SHEX0")
        self.assertEqual(derived["ports"]["discharge"]["time_margin_percent"],"24.3")
        self.assertIsNone(derived["ports"]["discharge"]["draft_limit_m"])
        self.assertEqual(cells[0]["rate"],calculate(derived)["classes"]["Handysize"]["nominal"]["freight_usd_mt"])
