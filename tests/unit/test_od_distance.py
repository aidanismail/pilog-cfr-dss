from copy import deepcopy
from decimal import Decimal
import hashlib
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from pilog_cfr_dss.sources.od_distance import read_distance, resolve_distance, payload_bytes

SOURCE = ROOT / "docs/it_4/Simulasi Tarif Internasional_Mei 2025.xlsx"


class ODDistanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = read_distance(SOURCE, "Bontang", "Mundra", "UREA GRANULAR BULK")

    def test_correct_product_origin_destination_cell_and_unit(self):
        record = self.record
        self.assertEqual((record["value"], record["cell"], record["unit"]), ("3906", "H11", "NM"))
        self.assertEqual((record["origin_cell"], record["destination_cell"], record["product_cell"]), ("H5", "E11", "C6"))
        self.assertFalse(record["independent_navigation_verified"])
        self.assertEqual(record["source_sha256"], hashlib.sha256(SOURCE.read_bytes()).hexdigest())

    def test_resolver_selects_route_instead_of_reusing_case_distance(self):
        selected = resolve_distance(self.record["raw_payload"], "Gresik", "Mundra", "Urea")
        self.assertEqual((selected["cell"], selected["value"]), ("F11", "3414"))

    def test_product_group_is_resolved_separately(self):
        selected = resolve_distance(self.record["raw_payload"], "Bontang", "Mundra", "NPK")
        self.assertEqual(selected["cell"], "H20")

    def test_missing_origin_or_destination_has_no_plausible_fallback(self):
        for origin, destination in (("Unknown port", "Mundra"), ("Bontang", "Unknown port")):
            with self.subTest(origin=origin, destination=destination), self.assertRaisesRegex(ValueError, "OD_DISTANCE"):
                resolve_distance(self.record["raw_payload"], origin, destination, "Urea")

    def test_duplicate_route_rejected(self):
        raw = deepcopy(self.record["raw_payload"])
        raw["cells"].update(E12="Mundra")
        with self.assertRaisesRegex(ValueError, "ROUTE_NOT_UNIQUE"):
            resolve_distance(raw, "Bontang", "Mundra", "Urea")

    def test_zero_negative_nonfinite_or_missing_distance_rejected(self):
        for value in (0, -1, "NaN", "Infinity", None):
            raw = deepcopy(self.record["raw_payload"]); raw["cells"]["H11"] = value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "INVALID_OD_DISTANCE_VALUE"):
                resolve_distance(raw, "Bontang", "Mundra", "Urea")

    def test_wrong_unit_not_reinterpreted_as_nm(self):
        raw = deepcopy(self.record["raw_payload"]); raw["unit"] = "km"
        with self.assertRaisesRegex(ValueError, "UNIT_OR_SHEET"):
            resolve_distance(raw, "Bontang", "Mundra", "Urea")

    def test_payload_bytes_stable_and_matching_hash(self):
        raw = self.record["raw_payload"]
        self.assertEqual(payload_bytes(raw), payload_bytes(deepcopy(raw)))
        self.assertEqual(hashlib.sha256(payload_bytes(raw)).hexdigest(), self.record["payload_sha256"])
