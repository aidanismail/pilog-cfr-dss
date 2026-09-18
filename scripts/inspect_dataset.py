from __future__ import annotations
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


EXPECTED_HEADERS = ["No", "Variable", "Value"]

ROUTE_VARIABLES = {
      "Loading port": "Bontang",
      "Discharging port": "ECI",
  }


def load_dataset(dataset_path: Path) -> list[dict[str, str]]:
      with dataset_path.open(
          "r",
          encoding="utf-8-sig",
          newline="",
      ) as file:
          reader = csv.DictReader(file)

          if reader.fieldnames != EXPECTED_HEADERS:
              raise ValueError(
                  "Header dataset tidak sesuai.\n"
                  f"Ditemukan: {reader.fieldnames}\n"
                  f"Diharapkan: {EXPECTED_HEADERS}"
              )

          rows = list(reader)

      return rows

def parse_number(value: str) -> float | None:
      cleaned_value = value.strip()

      if not cleaned_value:
          return None

      try:
          return float(cleaned_value)
      except ValueError:
          return None

def inspect_structure(rows: list[dict[str, str]]) -> dict:
      variables = [
          row.get("Variable", "").strip()
          for row in rows
      ]

      values = [
          row.get("Value", "").strip()
          for row in rows
      ]

      numbers = []
      texts = []
      empty_values = []

      for row in rows:
          variable = row.get("Variable", "").strip()
          value = row.get("Value", "").strip()

          if not value:
              empty_values.append(variable)
              continue

          parsed_number = parse_number(value)

          if parsed_number is None:
              texts.append(variable)
          else:
              numbers.append(variable)

      duplicate_variables = sorted(
          variable
          for variable, count in Counter(variables).items()
          if variable and count > 1
      )

      missing_variables = sorted(
          variable
          for variable in variables
          if not variable
      )

      row_numbers = []

      for row in rows:
          raw_number = row.get("No", "").strip()

          try:
              row_numbers.append(int(raw_number))
          except ValueError:
              pass

      expected_numbers = list(range(1, len(rows) + 1))
      numbering_is_sequential = row_numbers == expected_numbers

      return {
          "row_count": len(rows),
          "variable_count": len(variables),
          "unique_variable_count": len(set(variables)),
          "numeric_value_count": len(numbers),
          "text_value_count": len(texts),
          "empty_value_count": len(empty_values),
          "empty_variables": empty_values,
          "duplicate_variables": duplicate_variables,
          "missing_variable_names": missing_variables,
          "numbering_is_sequential": numbering_is_sequential,
          "numeric_variables": numbers,
          "text_variables": texts,
          "all_variables": variables,
          "all_values": values,
      }


def inspect_route(rows: list[dict[str, str]]) -> dict:
      values_by_variable = {
          row.get("Variable", "").strip(): row.get("Value",
          "").strip()
          for row in rows
      }

      route_results = {}

      for variable, expected_value in ROUTE_VARIABLES.items():
          actual_value = values_by_variable.get(variable)

          route_results[variable] = {
              "expected": expected_value,
              "actual": actual_value,
              "matches": actual_value == expected_value,
          }

      route_is_consistent = all(
          result["matches"]
          for result in route_results.values()
      )

      return {
          "expected_experimental_route": "Bontang → ECI",
          "route_is_consistent": route_is_consistent,
          "checks": route_results,
      }


def build_report(
      dataset_path: Path,
      rows: list[dict[str, str]],
  ) -> dict:
      structure_report = inspect_structure(rows)
      route_report = inspect_route(rows)

      return {
          "mode": "simulation",
          "status": "advisory-only",
          "dataset": {
              "file_name": dataset_path.name,
              "path": str(dataset_path),
              "grain": "one scenario parameter register",
              "route_context": (
                  "Bontang → ECI experimental scenario; "
                  "route override from Aqaba-based data"
              ),
          },
          "inspection": structure_report,
          "route_check": route_report,
          "run": {
              "executed_at_utc": datetime.now(
                  timezone.utc
              ).isoformat(),
              "batch": "B1-inspect",
          },
      }


def main() -> None:
      repository_root = Path(__file__).resolve().parents[1]
      dataset_path = repository_root / "data" / "dataset_ready.csv"
      output_path = (
          repository_root
          / "outputs"
          / "dataset_inspection.json"
      )

      if not dataset_path.exists():
          raise FileNotFoundError(
              f"Dataset tidak ditemukan: {dataset_path}"
          )

      rows = load_dataset(dataset_path)
      report = build_report(dataset_path, rows)

      print(json.dumps(
          report,
          indent=2,
          ensure_ascii=False,
      ))

      output_path.parent.mkdir(
          parents=True,
          exist_ok=True,
      )

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

      print(
          f"\nLaporan inspeksi tersimpan di: {output_path}"
      )


if __name__ == "__main__":
      main()