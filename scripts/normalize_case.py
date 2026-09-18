from __future__ import annotations
import json
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path


UNIT_PATTERN = re.compile(
      r"\(([^()]*)\)"
  )


def load_json(file_path: Path) -> dict:
      with file_path.open(
          "r",
          encoding="utf-8",
      ) as file:
          return json.load(file)


def split_label_and_unit(
      label: str,
  ) -> tuple[str, str | None]:
      match = UNIT_PATTERN.search(label)

      if not match:
          return label.strip(), None

      unit = match.group(1).strip()

      clean_label = UNIT_PATTERN.sub(
          "",
          label,
      ).strip()

      return clean_label, unit


def parse_numeric_value(
      raw_value: str,
  ) -> float | None:
      cleaned_value = raw_value.strip()

      if not cleaned_value:
          return None

      try:
          decimal_value = Decimal(cleaned_value)
      except InvalidOperation:
          return None

      return float(decimal_value)


def detect_data_type(
      raw_value: str,
  ) -> str:
      if not raw_value.strip():
          return "empty"

      if parse_numeric_value(raw_value) is not None:
          return "number"

      normalized_value = raw_value.strip().lower()

      if normalized_value in {
          "yes",
          "no",
          "true",
          "false",
      }:
          return "boolean_or_flag"

      return "text"


def detect_currency(
      unit: str | None,
  ) -> str | None:
      if not unit:
          return None

      upper_unit = unit.upper()

      if "USD" in upper_unit:
          return "USD"

      if "IDR" in upper_unit:
          return "IDR"

      if "EUR" in upper_unit:
          return "EUR"

      return None


def normalize_parameter(
      parameter_key: str,
      parameter: dict,
  ) -> dict:
      raw_label = parameter["label"]
      raw_value = parameter["raw_value"]

      clean_label, explicit_unit = split_label_and_unit(
          raw_label
      )

      data_type = detect_data_type(raw_value)
      numeric_value = parse_numeric_value(raw_value)

      if data_type == "number":
          normalized_value = numeric_value
      else:
          normalized_value = raw_value.strip()

      return {
          "parameter_key": parameter_key,
          "label": clean_label,
          "original_label": raw_label,
          "raw_value": raw_value,
          "normalized_value": normalized_value,
          "data_type": data_type,
          "unit": explicit_unit,
          "currency": detect_currency(explicit_unit),
          "unit_status": (
              "explicit"
              if explicit_unit
              else "missing_from_label"
          ),
          "source_row": parameter["source_row"],
          "source_column": parameter["source_column"],
          "transformation": {
              "trimmed_whitespace": True,
              "numeric_conversion": data_type == "number",
              "unit_conversion": False,
              "currency_conversion": False,
              "business_adjustment": False,
          },
          "normalization_status": (
              "normalized"
              if data_type != "empty"
              else "empty"
          ),
      }


def build_normalized_case(
      case: dict,
  ) -> dict:
      raw_parameters = case.get(
          "parameters",
          {},
      )

      normalized_parameters = {}

      for parameter_key, parameter in raw_parameters.items():
          normalized_parameters[parameter_key] = (
              normalize_parameter(
                  parameter_key,
                  parameter,
              )
          )

      missing_units = [
          parameter_key
          for parameter_key, parameter
          in normalized_parameters.items()
          if parameter["unit_status"]
          == "missing_from_label"
      ]

      return {
          "case_id": case["case_id"],
          "mode": "simulation",
          "status": "advisory-only",
          "route": case["route"],
          "dataset": case["dataset"],
          "parameters": normalized_parameters,
          "normalization": {
              "batch": "B4-normalize",
              "normalized_at_utc": datetime.now(
                  timezone.utc
              ).isoformat(),
              "numeric_conversion_applied": True,
              "unit_conversion_applied": False,
              "currency_conversion_applied": False,
              "business_adjustment_applied": False,
              "missing_unit_parameters": missing_units,
          },
      }


def main() -> None:
      repository_root = Path(__file__).resolve().parents[1]

      input_path = (
          repository_root
          / "outputs"
          / "case_bontang_eci.json"
      )

      output_path = (
          repository_root
          / "outputs"
          / "case_bontang_eci_normalized.json"
      )

      if not input_path.exists():
          raise FileNotFoundError(
              "Output Batch 2 belum ditemukan. "
              "Jalankan ingest_case.py terlebih dahulu."
          )

      case = load_json(input_path)
      normalized_case = build_normalized_case(case)

      with output_path.open(
          "w",
          encoding="utf-8",
      ) as file:
          json.dump(
              normalized_case,
              file,
              indent=2,
              ensure_ascii=False,
          )

      missing_units = normalized_case[
          "normalization"
      ]["missing_unit_parameters"]

      print(
          json.dumps(
              {
                  "case_id": normalized_case["case_id"],
                  "route": normalized_case["route"],
                  "parameter_count": len(
                      normalized_case["parameters"]
                  ),
                  "missing_unit_count": len(
                      missing_units
                  ),
                  "unit_conversion_applied": False,
                  "business_adjustment_applied": False,
                  "output": str(output_path),
              },
              indent=2,
              ensure_ascii=False,
          )
      )


if __name__ == "__main__":
      main()