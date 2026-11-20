from decimal import Decimal
from pathlib import Path
import unittest

from pilog_cfr_dss.application.freight_desk import evaluate, export_case, import_case, matrix
from pilog_cfr_dss.reporting.commercial_brief import commercial_brief


ROOT = Path(__file__).resolve().parents[2]
PACKAGES = ROOT / "outputs/test_cases"


def load(name="pilog_open_hire"):
    return import_case((PACKAGES / f"fd3_risk_{name}.json").read_bytes())


def handysize(result):
    return result["risk_assessment"]["classes"]["Handysize"]


class RiskMitigationTests(unittest.TestCase):
    def test_fixed_freight_and_open_hire_turn_surplus_into_deficit(self):
        case = load()
        result = evaluate(case)
        details = handysize(result)
        hire = details["exposures"]["hire"]
        stress = details["scenarios"][0]
        self.assertEqual(hire["owner"], "PILOG")
        self.assertEqual(hire["break_even_usd_day"].quantize(Decimal(".01")), Decimal("18230.99"))
        self.assertEqual(hire["quote_gap_usd_day"].quantize(Decimal(".01")), Decimal("122.01"))
        self.assertEqual(stress["delta_usd"].quantize(Decimal(".01")), Decimal("45031.88"))
        self.assertEqual(stress["surplus_usd"].quantize(Decimal(".01")), Decimal("-2747.19"))
        self.assertEqual(result["risk_assessment"]["primary"]["driver"], "hire")
        self.assertIn("Kajian beli FFA", commercial_brief(result))
        self.assertEqual(result["risk_assessment"], evaluate(import_case(export_case(case)))["risk_assessment"])
        case.pop("risk_assessment")
        self.assertEqual(result["classes"], evaluate(case)["classes"])

    def test_pi_physical_freight_stress_only_changes_pi_cost(self):
        result = evaluate(load("pi_open_freight"))
        risk = result["risk_assessment"]
        scenario = handysize(result)["scenarios"][0]
        self.assertEqual(risk["primary"]["owner"], "PI")
        self.assertEqual(scenario["delta_usd"], Decimal(58000))
        self.assertNotIn("surplus_usd", scenario)
        self.assertIsNone(result["classes"]["Handysize"]["nominal"]["commercial"])

    def test_unknown_status_or_changed_voyage_only_gives_planning_sensitivity(self):
        original = load()
        for change in ("indicative", "scope"):
            with self.subTest(change=change):
                case = import_case(export_case(original))
                if change == "indicative":
                    case["risk_assessment"]["commitments"]["freight"]["status"] = "indicative"
                else:
                    case["cargo_mt"] = "28000"
                details = handysize(evaluate(case))
                self.assertIsNone(details["exposures"]["hire"]["open_share"])
                self.assertEqual(details["scenarios"][0]["basis"], "Sensitivitas perencanaan")
                self.assertFalse(details["exposures"]["hire"]["options"])

    def test_fixed_hire_does_not_close_delay_or_demurrage_exposure(self):
        case = load()
        risk = case["risk_assessment"]
        risk["commitments"]["charter"].update(status="binding", basis="fixed", coverage_percent="100", rate="16353")
        risk["stresses"]["load_wait"] = "1"
        risk["port_delay"] = {"payer": "PILOG", "evidence": "DEMO DA-01"}
        risk["demurrage"] = {"recoverable_usd": "5000", "evidence": "DEMO DEM-01", "basis": "DEMO buyer perlu bayar 1 hari x 5000 USD"}
        result = evaluate(case)
        stresses = {row["driver"]: row for row in handysize(result)["scenarios"]}
        self.assertEqual(stresses["hire"]["delta_usd"], 0)
        self.assertGreater(stresses["load_wait"]["delta_usd"], 16353)
        self.assertEqual(stresses["load_wait"]["delta_days"], 1)
        self.assertEqual(result["risk_assessment"]["demurrage"]["recoverable_usd"], 5000)
        risk["demurrage"]["basis"] = ""
        self.assertIsNone(evaluate(case)["risk_assessment"]["demurrage"]["recoverable_usd"])

    def test_partial_hire_scope_and_bunker_coverage(self):
        case = load()
        risk = case["risk_assessment"]
        risk["commitments"]["charter"].update(status="binding", basis="fixed", coverage_percent="50", rate="16353")
        risk["LSMGO"] = {"payer": "PILOG", "status": "binding", "basis": "fixed", "coverage_percent": "50", "evidence": "DEMO LSMGO-01"}
        risk["stresses"].update(LSMGO="100", cargo="50000")
        details = handysize(evaluate(case))
        self.assertEqual(details["exposures"]["hire"]["open_share"], Decimal(".5"))
        stresses = {row["driver"]: row for row in details["scenarios"]}
        self.assertEqual(stresses["hire"]["delta_usd"].quantize(Decimal(".01")), Decimal("22515.94"))
        self.assertGreater(stresses["LSMGO"]["delta_usd"], 0)
        self.assertEqual(stresses["cargo"]["status"], "Skenario tidak lolos kapasitas")
        risk["commitments"]["freight"]["coverage_percent"] = "75"
        self.assertIsNone(handysize(evaluate(case))["exposures"]["hire"]["open_share"])

    def test_short_ffa_and_coa_require_committed_hire_and_open_revenue(self):
        case = load()
        risk = case["risk_assessment"]
        risk["commitments"]["charter"].update(status="binding", basis="fixed", coverage_percent="100", rate="16353")
        risk["commitments"]["freight"].update(status="open", evidence="DEMO belum ada kargo mengikat")
        risk["stresses"]["selling_freight"] = "-2"
        details = handysize(evaluate(case))
        self.assertEqual([x[0] for x in details["exposures"]["selling_freight"]["options"]], ["Kajian jual FFA"])
        self.assertEqual(details["scenarios"][1]["delta_usd"], -58000)
        risk["recurring_program"] = True
        self.assertEqual(handysize(evaluate(case))["exposures"]["selling_freight"]["options"][0][0], "COA bertarif tetap")

    def test_matrix_and_invalid_risk_package(self):
        case = load()
        route = [tuple(case["ports"][side][key] for key in ("name", "country")) for side in ("load", "discharge")]
        cell = matrix(case, [route[0]], [route[1]], "Handysize", ROOT)[0]
        self.assertNotIn("risk_assessment", cell["result"])
        self.assertEqual(cell["delta"], 0)
        case["risk_assessment"]["commitments"]["freight"]["coverage_percent"] = "101"
        with self.assertRaisesRegex(ValueError, "maksimal 100%"):
            import_case(export_case(case))
