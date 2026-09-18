from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path


def parse_decimal(
      value: str,
      argument_name: str,
  ) -> Decimal:
      try:
          return Decimal(value)
      except InvalidOperation as error:
          raise ValueError(
              f"{argument_name} harus berupa angka: {value}"
          ) from error


def decimal_to_float(
      value: Decimal | None,
  ) -> float | None:
      if value is None:
          return None

      return float(value)


def load_case(case_path: Path) -> dict:
      with case_path.open(
          "r",
          encoding="utf-8",
      ) as file:
          return json.load(file)


def get_case_quantity(
      case: dict,
  ) -> Decimal | None:
      parameter = case.get("parameters", {}).get(
          "dwcc_cargo_quantity_mt"
      )

      if not parameter:
          return None

      raw_value = parameter.get("normalized_value")

      if raw_value is None:
          return None

      try:
          return Decimal(str(raw_value))
      except InvalidOperation:
          return None


def calculate_results(
      index_value: Decimal,
      alpha_value: Decimal,
      freight_selling_rate: Decimal,
      cfr_adjustment: Decimal,
      freight_cost: Decimal | None,
  ) -> dict:
      fob_value = index_value + alpha_value

      cfr_value = (
          fob_value
          + freight_selling_rate
          + cfr_adjustment
      )

      freight_margin = None

      if freight_cost is not None:
          freight_margin = (
              freight_selling_rate
              - freight_cost
          )

      return {
          "fob_usd_mt": decimal_to_float(fob_value),
          "cfr_usd_mt": decimal_to_float(cfr_value),
          "freight_margin_usd_mt": decimal_to_float(
              freight_margin
          ),
      }


def validate_inputs(
      index_value: Decimal,
      alpha_value: Decimal,
      freight_selling_rate: Decimal,
      cfr_adjustment: Decimal,
      freight_cost: Decimal | None,
  ) -> list[dict]:
      checks = []

      values = {
          "index_usd_mt": index_value,
          "alpha_usd_mt": alpha_value,
          "freight_selling_rate_usd_mt": (
              freight_selling_rate
          ),
          "cfr_adjustment_usd_mt": cfr_adjustment,
      }

      if freight_cost is not None:
          values["freight_cost_usd_mt"] = freight_cost

      for name, value in values.items():
          if value < 0:
              checks.append(
                  {
                      "check": f"non_negative_{name}",
                      "status": "WARN",
                      "message": (
                          f"{name} bernilai negatif. "
                          "Validasi bisnis diperlukan."
                      ),
                  }
              )
          else:
              checks.append(
                  {
                      "check": f"non_negative_{name}",
                      "status": "PASS",
                      "message": f"{name} tidak negatif.",
                  }
              )

      checks.append(
          {
              "check": "common_unit",
              "status": "PASS",
              "message": (
                  "Semua input kalkulasi diperlakukan "
                  "sebagai USD/MT."
              ),
          }
      )

      checks.append(
          {
              "check": "business_basis",
              "status": "WARN",
              "message": (
                  "Basis Index, Alpha, Freight, dan A "
                  "harus divalidasi mentor."
              ),
          }
      )

      return checks


def main() -> None:
      parser = argparse.ArgumentParser(
          description=(
              "Batch 5 pricing calculation "
              "untuk simulasi PILOG CFR"
          )
      )

      parser.add_argument(
          "--index",
          required=True,
          help="Market price index dalam USD/MT",
      )

      parser.add_argument(
          "--alpha",
          required=True,
          help="Alpha dalam USD/MT",
      )

      parser.add_argument(
          "--freight-selling-rate",
          required=True,
          help="Freight selling rate dalam USD/MT",
      )

      parser.add_argument(
          "--adjustment",
          required=True,
          help="CFR adjustment A dalam USD/MT",
      )

      parser.add_argument(
          "--freight-cost",
          required=False,
          help=(
              "Relevant freight cost dalam USD/MT; "
              "opsional untuk margin"
          ),
      )

      args = parser.parse_args()

      repository_root = Path(__file__).resolve().parents[1]

      case_path = (
          repository_root
          / "outputs"
          / "case_bontang_eci_normalized.json"
      )

      output_path = (
          repository_root
          / "outputs"
          / "pricing_calculation.json"
      )

      if not case_path.exists():
          raise FileNotFoundError(
              "Output Batch 4 belum ditemukan."
          )

      case = load_case(case_path)

      index_value = parse_decimal(
          args.index,
          "--index",
      )

      alpha_value = parse_decimal(
          args.alpha,
          "--alpha",
      )

      freight_selling_rate = parse_decimal(
          args.freight_selling_rate,
          "--freight-selling-rate",
      )

      cfr_adjustment = parse_decimal(
          args.adjustment,
          "--adjustment",
      )

      freight_cost = None

      if args.freight_cost is not None:
          freight_cost = parse_decimal(
              args.freight_cost,
              "--freight-cost",
          )

      checks = validate_inputs(
          index_value=index_value,
          alpha_value=alpha_value,
          freight_selling_rate=freight_selling_rate,
          cfr_adjustment=cfr_adjustment,
          freight_cost=freight_cost,
      )

      results = calculate_results(
          index_value=index_value,
          alpha_value=alpha_value,
          freight_selling_rate=freight_selling_rate,
          cfr_adjustment=cfr_adjustment,
          freight_cost=freight_cost,
      )

      quantity = get_case_quantity(case)

      report = {
          "case_id": case["case_id"],
          "mode": "simulation",
          "status": "advisory-only",
          "calculation_status": "CALCULATED",
          "route": case["route"],
          "input_basis": {
              "index_unit": "USD/MT",
              "alpha_unit": "USD/MT",
              "freight_selling_rate_unit": "USD/MT",
              "cfr_adjustment_unit": "USD/MT",
              "freight_cost_unit": "USD/MT",
              "index_source": "manual simulation input",
              "alpha_source": "manual simulation input",
              "freight_source": (
                  "explicit CLI simulation input"
              ),
          },
          "inputs": {
              "index_usd_mt": decimal_to_float(
                  index_value
              ),
              "alpha_usd_mt": decimal_to_float(
                  alpha_value
              ),
              "freight_selling_rate_usd_mt": (
                  decimal_to_float(
                      freight_selling_rate
                  )
              ),
              "cfr_adjustment_usd_mt": (
                  decimal_to_float(
                      cfr_adjustment
                  )
              ),
              "freight_cost_usd_mt": decimal_to_float(
                  freight_cost
              ),
              "cargo_quantity_mt": decimal_to_float(
                  quantity
              ),
          },
          "formulas": {
              "fob": "Index + Alpha",
              "cfr": "FOB + Freight + A",
              "freight_margin": (
                  "Freight selling rate - Freight cost"
              ),
          },
          "results": results,
          "quality_checks": checks,
          "decision": {
              "choice_made": False,
              "recommendation": None,
              "reason": (
                  "Batch 5 hanya menghitung; "
                  "belum melakukan choice."
              ),
          },
          "run": {
              "batch": "B5-calculate",
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
              "route": report["route"],
              "fob_usd_mt": results["fob_usd_mt"],
              "cfr_usd_mt": results["cfr_usd_mt"],
              "freight_margin_usd_mt": (
                  results["freight_margin_usd_mt"]
              ),
              "choice_made": False,
              "output": str(output_path),
          },
          indent=2,
          ensure_ascii=False,
      ))


if __name__ == "__main__":
      main()