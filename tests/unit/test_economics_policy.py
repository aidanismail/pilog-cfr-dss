from __future__ import annotations

import sys
import unittest
from decimal import Decimal as D
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from pilog_cfr_dss.calculations.capacity import gross_dwt_screen
from pilog_cfr_dss.calculations.economics import required_rate_net_of_commission_usd_mt


class EconomicsPolicyTests(unittest.TestCase):
    def test_required_rate_reconciles_net_target_after_commission(self) -> None:
        rate = required_rate_net_of_commission_usd_mt(D("800000"), D("100000"), D("40000"), D("0.1"))
        self.assertEqual(rate, D("25"))
        gross = rate * D("40000")
        self.assertEqual(gross - gross * D("0.1") - D("800000"), D("100000"))
        with self.assertRaisesRegex(ValueError, "INVALID_NET_REQUIRED_RATE_INPUT"):
            required_rate_net_of_commission_usd_mt(D("1"), D("1"), D("1"), D("1"))

    def test_gross_dwt_screen_boundaries(self) -> None:
        self.assertEqual(
            gross_dwt_screen(D("58000"), D("45000"), D("50000"), D("60000")),
            (True, "PRELIMINARY_DWT_SCREEN_PASS"),
        )
        self.assertEqual(
            gross_dwt_screen(D("58000"), D("45000"), D("20000"), D("40000")),
            (False, "CARGO_EXCEEDS_CLASS_MAX_DWT"),
        )
        self.assertEqual(
            gross_dwt_screen(D("58000"), D("60001"), D("50000"), D("60000")),
            (False, "CARGO_EXCEEDS_CLASS_MAX_DWT"),
        )
        with self.assertRaisesRegex(ValueError, "INVALID_DWT_SCREEN_INPUT"):
            gross_dwt_screen(D("58000"), D("-1"), D("50000"), D("60000"))


if __name__ == "__main__":
    unittest.main()
