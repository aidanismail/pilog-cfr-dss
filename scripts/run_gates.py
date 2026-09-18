from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path


def load_json(file_path: Path) -> dict:
      with file_path.open(
          "r",
          encoding="utf-8",
      ) as file:
          return json.load(file)


def evaluate_boolean_checks(
      checks: dict,
  ) -> dict:
      failed = []
      unknown = []

      for check_name, value in checks.items():
          if check_name == "margin_floor_usd_mt":
              continue

          if value is False:
              failed.append(check_name)

          if value is None:
              unknown.append(check_name)

      if failed:
          status = "FAIL"

      elif unknown:
          status = "INCOMPLETE"

      else:
          status = "PASS"

      return {
          "status": status,
          "failed_checks": failed,
          "unknown_checks": unknown,
      }


def evaluate_gate_1(
      gate_1_inputs: dict,
  ) -> dict:
      result = evaluate_boolean_checks(
          gate_1_inputs
      )

      if result["status"] == "PASS":
          outcome = "CFR_ELIGIBLE"

      elif result["status"] == "FAIL":
          outcome = "FOB_RECOMMENDED"

      else:
          outcome = "HOLD_INCOMPLETE"

      return {
          "gate": "Gate 1",
          "purpose": (
              "Memeriksa kelayakan awal CFR."
          ),
          "outcome": outcome,
          "checks": result,
      }


def evaluate_scenario(
      scenario: dict,
      gate_2_inputs: dict,
  ) -> dict:
      scenario_id = scenario["scenario_id"]
      sales_term = scenario["sales_term"]
      feasible = scenario.get("feasible", False)
      comparable = scenario.get(
          "comparable",
          False,
      )

      if sales_term == "FOB":
          return {
              "scenario_id": scenario_id,
              "outcome": "FOB_BASELINE",
              "recommendation_eligible": True,
              "reasons": [
                  "Scenario digunakan sebagai baseline.",
              ],
          }

      if not feasible:
          return {
              "scenario_id": scenario_id,
              "outcome": "INFEASIBLE",
              "recommendation_eligible": False,
              "reasons": [
                  "Scenario ditandai tidak feasible."
              ],
          }

      if not comparable:
          return {
              "scenario_id": scenario_id,
              "outcome": "CFR_CONDITIONAL",
              "recommendation_eligible": False,
              "reasons": [
                  "Basis scenario belum comparable.",
              ],
          }

      required_checks = [
          "operational_feasibility",
          "customer_competitiveness",
          "cash_and_credit_acceptable",
          "market_basis_comparable",
          "clause_risk_acceptable",
          "risk_policy_acceptable",
          "required_approvals_complete",
      ]

      failed_checks = [
          check_name
          for check_name in required_checks
          if gate_2_inputs.get(check_name)
          is False
      ]

      unknown_checks = [
          check_name
          for check_name in required_checks
          if gate_2_inputs.get(check_name)
          is None
      ]

      results = scenario.get(
          "results",
          {},
      )

      margin = results.get(
          "freight_margin_usd_mt"
      )

      margin_floor = gate_2_inputs.get(
          "margin_floor_usd_mt"
      )

      margin_below_floor = (
          margin is None
          or margin_floor is None
          or margin < margin_floor
      )

      reasons = []

      if failed_checks:
          reasons.append(
              "Ada Gate 2 check yang gagal."
          )

      if unknown_checks:
          reasons.append(
              "Ada Gate 2 check yang belum diketahui."
          )

      if margin_below_floor:
          reasons.append(
              "Margin berada di bawah floor "
              "atau belum tersedia."
          )

      if failed_checks or margin_below_floor:
          outcome = "FOB_RECOMMENDED"

      elif unknown_checks:
          outcome = "CFR_CONDITIONAL"

      else:
          outcome = "CFR_APPROVED"

      return {
          "scenario_id": scenario_id,
          "outcome": outcome,
          "recommendation_eligible": outcome
          == "CFR_APPROVED",
          "margin_usd_mt": margin,
          "margin_floor_usd_mt": margin_floor,
          "failed_checks": failed_checks,
          "unknown_checks": unknown_checks,
          "reasons": reasons,
      }


def evaluate_gate_2(
      scenarios: list[dict],
      gate_2_inputs: dict,
  ) -> dict:
      scenario_results = [
          evaluate_scenario(
              scenario,
              gate_2_inputs,
          )
          for scenario in scenarios
      ]

      approved = [
          result
          for result in scenario_results
          if result["outcome"]
          == "CFR_APPROVED"
      ]

      conditional = [
          result
          for result in scenario_results
          if result["outcome"]
          == "CFR_CONDITIONAL"
      ]

      if approved:
          overall_outcome = "CFR_APPROVED"

      elif conditional:
          overall_outcome = "CFR_CONDITIONAL"

      else:
          overall_outcome = "FOB_RECOMMENDED"

      return {
          "gate": "Gate 2",
          "purpose": (
              "Memeriksa keputusan akhir "
              "FOB versus CFR."
          ),
          "outcome": overall_outcome,
          "scenario_results": scenario_results,
      }


def main() -> None:
      repository_root = Path(__file__).resolve().parents[1]

      scenario_path = (
          repository_root
          / "outputs"
          / "scenario_comparison.json"
      )

      gate_input_path = (
          repository_root
          / "data"
          / "reference"
          / "gate_inputs.json"
      )

      output_path = (
          repository_root
          / "outputs"
          / "gate_evaluation.json"
      )

      if not scenario_path.exists():
          raise FileNotFoundError(
              "Output Batch 6 belum ditemukan."
          )

      if not gate_input_path.exists():
          raise FileNotFoundError(
              "gate_inputs.json belum ditemukan."
          )

      scenario_report = load_json(
          scenario_path
      )

      gate_inputs = load_json(
          gate_input_path
      )

      gate_1 = evaluate_gate_1(
          gate_inputs["gate_1"]
      )

      if gate_1["outcome"] != "CFR_ELIGIBLE":
          gate_2 = {
              "gate": "Gate 2",
              "outcome": "NOT_STARTED",
              "reason": (
                  "Gate 1 belum menyatakan CFR eligible."
              ),
              "scenario_results": [],
          }

          overall_outcome = gate_1["outcome"]

      else:
          gate_2 = evaluate_gate_2(
              scenario_report["scenarios"],
              gate_inputs["gate_2"],
          )

          overall_outcome = gate_2["outcome"]

      report = {
          "case_id": scenario_report["case_id"],
          "mode": "simulation",
          "status": "advisory-only",
          "batch": "B7-gates",
          "gate_1": gate_1,
          "gate_2": gate_2,
          "overall_outcome": overall_outcome,
          "choice_made": False,
          "human_approval_required": True,
          "run": {
              "executed_at_utc": datetime.now(
                  timezone.utc
              ).isoformat(),
          },
      }

      with output_path.open(
          "w",
          encoding="utf-8",
      ) as file:
          json.dump(
              report,
              file,
              indent=2,
              ensure_ascii=False,
          )

      print(json.dumps(
          {
              "case_id": report["case_id"],
              "gate_1_outcome": gate_1[
                  "outcome"
              ],
              "gate_2_outcome": gate_2[
                  "outcome"
              ],
              "overall_outcome": overall_outcome,
              "choice_made": report[
                  "choice_made"
              ],
              "human_approval_required": report[
                  "human_approval_required"
              ],
              "output": str(output_path),
          },
          indent=2,
          ensure_ascii=False,
      ))


if __name__ == "__main__":
      main()