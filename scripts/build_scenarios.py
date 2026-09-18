from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
def load_json(file_path: Path):
      with file_path.open(
          "r",
          encoding="utf-8",
      ) as file:
          return json.load(file)


def calculate_scenario(
      base_calculation: dict,
      scenario: dict,
  ) -> dict:
      inputs = base_calculation["inputs"]

      index_value = inputs["index_usd_mt"]
      alpha_value = inputs["alpha_usd_mt"]
      adjustment_value = inputs[
          "cfr_adjustment_usd_mt"
      ]

      sales_term = scenario["sales_term"]

      if sales_term == "FOB":
          return {
              "scenario_id": scenario["scenario_id"],
              "scenario_name": scenario[
                  "scenario_name"
              ],
              "sales_term": sales_term,
              "vessel_option": scenario[
                  "vessel_option"
              ],
              "feasible": scenario["feasible"],
              "comparable": scenario["comparable"],
              "source": scenario["source"],
              "note": scenario["note"],
              "inputs": {
                  "index_usd_mt": index_value,
                  "alpha_usd_mt": alpha_value,
                  "freight_selling_rate_usd_mt": None,
                  "freight_cost_usd_mt": None,
                  "cfr_adjustment_usd_mt": None,
              },
              "results": {
                  "fob_usd_mt": (
                      index_value + alpha_value
                  ),
                  "cfr_usd_mt": None,
                  "freight_margin_usd_mt": None,
              },
              "calculation_status": "CALCULATED",
          }

      freight_selling_rate = scenario.get(
          "freight_selling_rate_usd_mt"
      )

      freight_cost = scenario.get(
          "freight_cost_usd_mt"
      )

      if freight_selling_rate is None:
          return {
              **scenario,
              "calculation_status": "BLOCKED",
              "block_reason": (
                  "Freight selling rate belum tersedia."
              ),
          }

      if freight_cost is None:
          return {
              **scenario,
              "calculation_status": "BLOCKED",
              "block_reason": (
                  "Freight cost belum tersedia."
              ),
          }

      fob_value = index_value + alpha_value

      cfr_value = (
          fob_value
          + freight_selling_rate
          + adjustment_value
      )

      freight_margin = (
          freight_selling_rate
          - freight_cost
      )

      return {
          "scenario_id": scenario["scenario_id"],
          "scenario_name": scenario[
              "scenario_name"
          ],
          "sales_term": sales_term,
          "vessel_option": scenario[
              "vessel_option"
          ],
          "feasible": scenario["feasible"],
          "comparable": scenario["comparable"],
          "source": scenario["source"],
          "note": scenario["note"],
          "inputs": {
              "index_usd_mt": index_value,
              "alpha_usd_mt": alpha_value,
              "freight_selling_rate_usd_mt": (
                  freight_selling_rate
              ),
              "freight_cost_usd_mt": freight_cost,
              "cfr_adjustment_usd_mt": (
                  adjustment_value
              ),
          },
          "results": {
              "fob_usd_mt": fob_value,
              "cfr_usd_mt": cfr_value,
              "freight_margin_usd_mt": freight_margin,
          },
          "calculation_status": "CALCULATED",
      }


def main() -> None:
      repository_root = Path(__file__).resolve().parents[1]

      calculation_path = (
          repository_root
          / "outputs"
          / "pricing_calculation.json"
      )

      scenario_input_path = (
          repository_root
          / "data"
          / "reference"
          / "scenario_inputs.json"
      )

      output_path = (
          repository_root
          / "outputs"
          / "scenario_comparison.json"
      )

      if not calculation_path.exists():
          raise FileNotFoundError(
              "Output Batch 5 belum ditemukan."
          )

      if not scenario_input_path.exists():
          raise FileNotFoundError(
              "scenario_inputs.json belum ditemukan."
          )

      base_calculation = load_json(
          calculation_path
      )

      scenarios = load_json(
          scenario_input_path
      )

      if not isinstance(scenarios, list):
          raise ValueError(
              "scenario_inputs.json harus berupa array."
          )

      calculated_scenarios = [
          calculate_scenario(
              base_calculation,
              scenario,
          )
          for scenario in scenarios
      ]

      report = {
          "case_id": base_calculation["case_id"],
          "mode": "simulation",
          "status": "advisory-only",
          "batch": "B6-scenario",
          "choice_made": False,
          "scenario_count": len(
              calculated_scenarios
          ),
          "scenarios": calculated_scenarios,
          "comparison_notes": [
              (
                  "Scenario belum diranking "
                  "atau dipilih."
              ),
              (
                  "Angka hanya comparable jika "
                  "basis, unit, route, date, dan "
                  "cost boundary sama."
              ),
              (
                  "Scenario dengan comparable=false "
                  "tidak boleh dipakai sebagai "
                  "dasar keputusan final."
              ),
          ],
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
              "scenario_count": report[
                  "scenario_count"
              ],
              "choice_made": report[
                  "choice_made"
              ],
              "output": str(output_path),
          },
          indent=2,
          ensure_ascii=False,
      ))


if __name__ == "__main__":
      main()