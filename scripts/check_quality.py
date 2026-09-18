from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
REQUIRED_PARAMETERS = [
      "cargo_description",
      "loading_port",
      "discharging_port",
      "laden_distance_nm",
      "ballast_distance_nm",
      "laden_speed_knots",
      "ballast_speed_knots",
      "dwt_mt",
      "dwcc_cargo_quantity_mt",
      "loading_rate_mt_day",
      "discharge_rate_mt_day",
      "fuel_oil_price_usd_mt",
      "diesel_oil_price_usd_mt",
      "other_voyage_costs_total_usd",
      "freight_rate_usd_mt",
  ]


NUMERIC_PARAMETERS = [
      "laden_distance_nm",
      "ballast_distance_nm",
      "laden_speed_knots",
      "ballast_speed_knots",
      "fuel_oil_consumption_laden_mt_day",
      "fuel_oil_consumption_ballast_mt_day",
      "diesel_consumption_at_sea_laden_mt_day",
      "diesel_consumption_at_sea_ballast_mt_day",
      "in_port_working_load_factor",
      "in_port_diesel_factor_kg_kwh",
      "auxiliary_engine_power_kw",
      "dwt_mt",
      "bunkers_allowance_mt",
      "constants_allowance_mt",
      "dwcc_cargo_quantity_mt",
      "loading_rate_mt_day",
      "discharge_rate_mt_day",
      "canal_transit_days",
      "fuel_oil_at_loading_port_mt",
      "fuel_oil_at_discharging_port_mt",
      "fuel_oil_price_usd_mt",
      "diesel_oil_price_usd_mt",
      "other_voyage_costs_total_usd",
      "daily_cost_assumption_usd_day",
      "hire_rate_usd_day",
      "freight_rate_usd_mt",
      "freight_commission_rate",
      "running_costs_usd_day",
      "voyage_expense_allocation_quantity_mt",
      "exchange_rate_idr_usd",
      "hire_comparison_days",
      "broker_fee_rate",
      "additional_commission_rate",
      "reference_dwt_mt",
      "ssw_draft_m",
      "tpc_mt_cm",
      "maximum_vessel_age_years",
      "length_overall_loa_m",
      "beam_m",
      "grain_capacity_cbm",
      "bale_capacity_cbm",
      "cargo_holds",
      "cargo_hatches",
      "cranes",
      "crane_capacity_each_mt",
      "grabs",
      "grab_capacity_each_cbm",
      "mfo_consumption_at_14_knots_laden_mt_day",
      "mfo_consumption_at_14_knots_ballast_mt_day",
      "mfo_consumption_at_13_knots_laden_mt_day",
      "mfo_consumption_at_13_knots_ballast_mt_day",
      "mfo_consumption_at_12_knots_laden_mt_day",
      "mfo_consumption_at_12_knots_ballast_mt_day",
      "mfo_consumption_at_11_knots_laden_mt_day",
      "mfo_consumption_at_11_knots_ballast_mt_day",
  ]


POSITIVE_PARAMETERS = [
      "laden_distance_nm",
      "ballast_distance_nm",
      "laden_speed_knots",
      "ballast_speed_knots",
      "fuel_oil_consumption_laden_mt_day",
      "fuel_oil_consumption_ballast_mt_day",
      "auxiliary_engine_power_kw",
      "dwt_mt",
      "dwcc_cargo_quantity_mt",
      "loading_rate_mt_day",
      "discharge_rate_mt_day",
      "fuel_oil_price_usd_mt",
      "diesel_oil_price_usd_mt",
      "other_voyage_costs_total_usd",
      "daily_cost_assumption_usd_day",
      "hire_rate_usd_day",
      "freight_rate_usd_mt",
      "running_costs_usd_day",
      "voyage_expense_allocation_quantity_mt",
      "exchange_rate_idr_usd",
  ]


NON_NEGATIVE_PARAMETERS = [
      "canal_transit_days",
      "fuel_oil_at_loading_port_mt",
      "fuel_oil_at_discharging_port_mt",
  ]


def load_case(case_path: Path) -> dict:
      with case_path.open(
          "r",
          encoding="utf-8",
      ) as file:
          return json.load(file)


def parse_number(raw_value: str) -> float | None:
      value = raw_value.strip()

      if not value:
          return None

      try:
          return float(value)
      except ValueError:
          return None


def add_check(
      checks: list[dict],
      check_name: str,
      status: str,
      message: str,
      fields: list[str] | None = None,
  ) -> None:
      checks.append(
          {
              "check": check_name,
              "status": status,
              "message": message,
              "fields": fields or [],
          }
      )


def check_required_parameters(
      parameters: dict,
      checks: list[dict],
  ) -> None:
      missing = [
          parameter
          for parameter in REQUIRED_PARAMETERS
          if parameter not in parameters
      ]

      empty = [
          parameter
          for parameter in REQUIRED_PARAMETERS
          if parameter in parameters
          and not parameters[parameter]["raw_value"].strip()
      ]

      if missing:
          add_check(
              checks,
              "required_parameters",
              "BLOCK",
              "Parameter wajib tidak ditemukan.",
              missing,
          )
      elif empty:
          add_check(
              checks,
              "required_parameters",
              "BLOCK",
              "Parameter wajib memiliki value kosong.",
              empty,
          )
      else:
          add_check(
              checks,
              "required_parameters",
              "PASS",
              "Semua parameter wajib tersedia dan tidak kosong.",
          )


def check_numeric_parameters(
      parameters: dict,
      checks: list[dict],
  ) -> None:
      invalid = []

      for parameter in NUMERIC_PARAMETERS:
          if parameter not in parameters:
              continue

          raw_value = parameters[parameter]["raw_value"]

          if parse_number(raw_value) is None:
              invalid.append(parameter)

      if invalid:
          add_check(
              checks,
              "numeric_values",
              "BLOCK",
              "Parameter yang seharusnya numerik tidak dapat dibaca.",
              invalid,
          )
      else:
          add_check(
              checks,
              "numeric_values",
              "PASS",
              "Semua parameter numerik yang tersedia dapat dibaca.",
          )


def check_value_ranges(
      parameters: dict,
      checks: list[dict],
  ) -> None:
      negative_values = []
      invalid_non_negative = []

      for parameter in POSITIVE_PARAMETERS:
          if parameter not in parameters:
              continue

          value = parse_number(
              parameters[parameter]["raw_value"]
          )

          if value is not None and value <= 0:
              negative_values.append(parameter)

      for parameter in NON_NEGATIVE_PARAMETERS:
          if parameter not in parameters:
              continue

          value = parse_number(
              parameters[parameter]["raw_value"]
          )

          if value is not None and value < 0:
              invalid_non_negative.append(parameter)

      if negative_values:
          add_check(
              checks,
              "positive_ranges",
              "BLOCK",
              "Parameter yang harus positif memiliki nilai nol/negatif.",
              negative_values,
          )
      else:
          add_check(
              checks,
              "positive_ranges",
              "PASS",
              "Parameter positif yang tersedia berada di atas nol.",
          )

      if invalid_non_negative:
          add_check(
              checks,
              "non_negative_ranges",
              "BLOCK",
              "Parameter yang boleh nol memiliki nilai negatif.",
              invalid_non_negative,
          )
      else:
          add_check(
              checks,
              "non_negative_ranges",
              "PASS",
              "Parameter non-negatif tidak memiliki nilai negatif.",
          )


def check_route(case: dict, checks: list[dict]) -> None:
      route = case.get("route", {})

      origin = route.get("origin")
      destination = route.get("destination")

      if origin == "Bontang" and destination == "ECI":
          add_check(
              checks,
              "experimental_route",
              "PASS",
              "Route eksperimen konsisten: Bontang → ECI.",
          )
      else:
          add_check(
              checks,
              "experimental_route",
              "BLOCK",
              "Route tidak sesuai skenario eksperimen Bontang ke ECI.",
              ["origin", "destination"],
          )


def check_semantic_warnings(
      parameters: dict,
      checks: list[dict],
  ) -> None:
      unit_in_variable_name = []

      for parameter in parameters.values():
          label = parameter["label"]

          if "(" in label and ")" in label:
              unit_in_variable_name.append(label)

      if unit_in_variable_name:
          add_check(
              checks,
              "embedded_units",
              "WARN",
              (
                  "Unit masih tertanam pada label Variable. "
                  "Pemisahan unit dilakukan pada batch normalize."
              ),
              unit_in_variable_name,
          )

      add_check(
          checks,
          "freshness",
          "WARN",
          (
              "Dataset belum memiliki metadata freshness/as-of "
              "untuk setiap input yang sensitif terhadap waktu."
          ),
      )

      add_check(
          checks,
          "route_override",
          "WARN",
          (
              "Route Aqaba telah diubah menjadi Bontang → ECI "
              "untuk simulasi. Field voyage harus divalidasi ulang "
              "untuk route eksperimen."
          ),
      )


def check_pricing_readiness(
      parameters: dict,
      checks: list[dict],
  ) -> None:
      pricing_parameters = [
          "market_price_index",
          "alpha",
          "freight_rate_usd_mt",
      ]

      missing = [
          parameter
          for parameter in pricing_parameters
          if parameter not in parameters
      ]

      if missing:
          add_check(
              checks,
              "pricing_readiness",
              "BLOCK",
              (
                  "Pricing CFR belum siap karena Index/Alpha/ Freight "
                  "belum lengkap sebagai parameter kanonis."
              ),
              missing,
          )
      else:
          add_check(
              checks,
              "pricing_readiness",
              "PASS",
              "Parameter minimum pricing CFR tersedia.",
          )


def summarize_status(checks: list[dict]) -> str:
      statuses = {
          check["status"]
          for check in checks
      }

      if "BLOCK" in statuses:
          return "BLOCK"

      if "WARN" in statuses:
          return "WARN"

      return "PASS"


def main() -> None:
      repository_root = Path(__file__).resolve().parents[1]

      case_path = (
          repository_root
          / "outputs"
          / "case_bontang_eci.json"
      )

      output_path = (
          repository_root
          / "outputs"
          / "case_quality_report.json"
      )

      if not case_path.exists():
          raise FileNotFoundError(
              "Jalankan Batch 2 terlebih dahulu."
          )

      case = load_case(case_path)
      parameters = case.get("parameters", {})

      checks: list[dict] = []

      check_required_parameters(
          parameters,
          checks,
      )

      check_numeric_parameters(
          parameters,
          checks,
      )

      check_value_ranges(
          parameters,
          checks,
      )

      check_route(
          case,
          checks,
      )

      check_semantic_warnings(
          parameters,
          checks,
      )

      check_pricing_readiness(
          parameters,
          checks,
      )

      report = {
          "mode": "simulation",
          "status": "advisory-only",
          "batch": "B3-quality",
          "case_id": case.get("case_id"),
          "overall_quality_status": summarize_status(
              checks
          ),
          "checks": checks,
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
          report,
          indent=2,
          ensure_ascii=False,
      ))

      print(
          f"\nLaporan kualitas tersimpan di: {output_path}"
      )


if __name__ == "__main__":
      main()