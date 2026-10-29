from decimal import Decimal, ROUND_DOWN, localcontext
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from pilog_cfr_dss.reporting.formatting import number_text, percent_text


class NumberFormattingTests(unittest.TestCase):
    def test_two_indonesian_decimals_with_half_up_and_sign(self):
        examples = {
            "23.3896": "23,39", "23.381": "23,38", "23.385": "23,39",
            "-23.385": "-23,39", "1234567.895": "1.234.567,90",
            "0": "0,00", "1": "1,00", "-0.004": "-0,00", "999.999": "1.000,00",
        }
        for value, expected in examples.items():
            with self.subTest(value=value):
                self.assertEqual(number_text(value), expected)

    def test_invalid_values_never_become_fake_zero(self):
        for value in (None, "", "bad", "NaN", "Infinity", "-Infinity"):
            with self.subTest(value=value):
                self.assertEqual(number_text(value), "—")

    def test_minimums_are_rounded_up_to_keep_recovery_sufficient(self):
        self.assertEqual(number_text("26.2114"), "26,21")
        self.assertEqual(number_text("26.2114", minimum=True), "26,22")
        self.assertEqual(number_text("22800.3525", minimum=True), "22.800,36")
        self.assertEqual(number_text("0.0001", minimum=True), "0,01")

    def test_display_is_independent_of_decimal_context(self):
        with localcontext() as context:
            context.prec = 5
            context.rounding = ROUND_DOWN
            self.assertEqual(number_text("1234567.895"), "1.234.567,90")
            self.assertEqual(context.prec, 5)
            self.assertEqual(context.rounding, ROUND_DOWN)

    def test_percent_has_two_decimals_and_preserves_fraction(self):
        value = Decimal("0.0625")
        self.assertEqual(percent_text(value), "6,25%")
        self.assertEqual(percent_text("0.01245"), "1,25%")
        self.assertEqual(percent_text("0"), "0,00%")
        self.assertEqual(percent_text(None), "—")
        self.assertEqual(value, Decimal("0.0625"))

    def test_formatting_does_not_quantize_the_source_decimal(self):
        value = Decimal("25.4513")
        self.assertEqual(number_text(value), "25,45")
        self.assertEqual(str(value), "25.4513")
