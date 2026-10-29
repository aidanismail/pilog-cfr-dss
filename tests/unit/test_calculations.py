from __future__ import annotations

import sys
import unittest
from decimal import Decimal as D
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from pilog_cfr_dss.calculations.capacity import deadweight_headroom_mt
from pilog_cfr_dss.calculations.costs import commission_usd, daily_cost_usd, total_cost_usd
from pilog_cfr_dss.calculations.fuel import fuel_cost_usd, port_diesel_mt, sea_fuel_mt
from pilog_cfr_dss.calculations.pricing import (
    cfr_usd_mt, fob_usd_mt, freight_cost_per_mt, gross_freight_revenue_usd,
    net_freight_contribution_usd, required_freight_rate_usd_mt,
)
from pilog_cfr_dss.calculations.voyage_days import port_days, sea_days, total_days
from pilog_cfr_dss.models.contracts import CostLine


class CalculationTests(unittest.TestCase):
    def test_voyage_days_and_fuel_units(self) -> None:
        self.assertEqual(sea_days(D("240"), D("10")), D("1"))
        self.assertEqual(port_days(D("10000"), D("5000")), D("2"))
        self.assertEqual(total_days(D("1"), D("2")), D("3"))
        self.assertEqual(sea_fuel_mt(D("2"), D("20")), D("40"))
        self.assertEqual(port_diesel_mt(D("1"), D("1000"), D("0.5"), D("0.2")), D("2.4"))
        self.assertEqual(fuel_cost_usd(D("2.4"), D("700")), D("1680"))

    def test_physical_boundaries(self) -> None:
        with self.assertRaisesRegex(ValueError, "INVALID_DISTANCE_OR_SPEED"):
            sea_days(D("100"), D("0"))
        with self.assertRaisesRegex(ValueError, "INVALID_CARGO_OR_HANDLING_RATE"):
            port_days(D("100"), D("0"))
        with self.assertRaisesRegex(ValueError, "INVALID_PORT_DIESEL_INPUT"):
            port_diesel_mt(D("1"), D("1000"), D("1.2"), D("0.2"))
        self.assertEqual(deadweight_headroom_mt(D("58000"), D("1800"), D("500"), D("45000")), D("10700"))

    def test_cost_boundary_and_double_count(self) -> None:
        lines = [
            CostLine("hire", D("100"), frozenset({"daily_vessel"})),
            CostLine("bunker", D("50"), frozenset({"fuel"})),
            CostLine("port_and_other", D("20"), frozenset({"port", "other"})),
        ]
        self.assertEqual(total_cost_usd(lines), D("170"))
        with self.assertRaisesRegex(ValueError, "DOUBLE_COUNTED_COST:port"):
            total_cost_usd([*lines, CostLine("second_port", D("10"), frozenset({"port"}))])
        self.assertEqual(daily_cost_usd(D("3"), D("13000")), D("39000"))

    def test_pricing_revenue_and_contribution(self) -> None:
        self.assertEqual(fob_usd_mt(D("250"), D("3")), D("253"))
        self.assertEqual(cfr_usd_mt(D("253"), D("20"), D("0")), D("273"))
        self.assertEqual(freight_cost_per_mt(D("800000"), D("40000")), D("20"))
        self.assertEqual(required_freight_rate_usd_mt(D("800000"), D("100000"), D("40000")), D("22.5"))
        gross = gross_freight_revenue_usd(D("25"), D("40000"))
        self.assertEqual(gross, D("1000000"))
        self.assertEqual(commission_usd(gross, [D("0.025"), D("0.0125")]), D("37500"))
        self.assertEqual(net_freight_contribution_usd(gross, D("37500"), D("800000")), D("162500"))
        with self.assertRaisesRegex(ValueError, "INVALID_REQUIRED_RATE_INPUT"):
            required_freight_rate_usd_mt(D("1"), D("1"), D("0"))
        with self.assertRaisesRegex(ValueError, "INVALID_COMMISSION_INPUT"):
            commission_usd(gross, [D("0.8"), D("0.3")])


if __name__ == "__main__":
    unittest.main()
