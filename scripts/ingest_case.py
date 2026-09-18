from __future__ import annotations

import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

EXPECTED_HEADERS = ["No", "Variable", "Value"]

def calculate_sha256(file_path: Path) -> str:
      sha256 = hashlib.sha256()

      with file_path.open("rb") as file:
          for chunk in iter(
              lambda: file.read(1024 * 1024),
              b"",
          ):
              sha256.update(chunk)

      return sha256.hexdigest()


def slugify_variable(variable: str) -> str:
      value = variable.strip().lower()

      value = re.sub(
          r"[^a-z0-9]+",
          "_",
          value,
      )

      value = value.strip("_")

      return value


def load_rows(dataset_path: Path) -> list[dict[str, str]]:
      with dataset_path.open(
          "r",
          encoding="utf-8-sig",
          newline="",
      ) as file:
          reader = csv.DictReader(file)

          if reader.fieldnames != EXPECTED_HEADERS:
              raise ValueError(
                  "Header CSV tidak sesuai.\n"
                  f"Ditemukan: {reader.fieldnames}\n"
                  f"Diharapkan: {EXPECTED_HEADERS}"
              )

          rows = list(reader)

      if not rows:
          raise ValueError("Dataset tidak memiliki baris data.")

      return rows


def build_parameters(
      rows: list[dict[str, str]],
  ) -> dict[str, dict]:
      parameters: dict[str, dict] = {}

      for row in rows:
          raw_no = row.get("No", "").strip()
          variable = row.get("Variable", "").strip()
          raw_value = row.get("Value", "")

          if not raw_no:
              raise ValueError(
                  "Kolom No kosong ditemukan."
              )

          if not variable:
              raise ValueError(
                  f"Variable kosong pada baris {raw_no}."
              )

          parameter_key = slugify_variable(variable)

          if not parameter_key:
              raise ValueError(
                  f"Variable tidak dapat dibuat menjadi key: "
                  f"{variable}"
              )

          if parameter_key in parameters:
              previous = parameters[parameter_key]

              raise ValueError(
                  "Variable duplikat setelah normalisasi:\n"
                  f"- key: {parameter_key}\n"
                  f"- baris sebelumnya: "
                  f"{previous['source_row']}\n"
                  f"- baris sekarang: {raw_no}"
              )

          parameters[parameter_key] = {
              "label": variable,
              "raw_value": raw_value,
              "source_row": int(raw_no),
              "source_column": "Value",
              "value_status": (
                  "empty"
                  if not raw_value.strip()
                  else "untyped"
              ),
          }

      return parameters


def build_case(
      dataset_path: Path,
      rows: list[dict[str, str]],
  ) -> dict:
      parameters = build_parameters(rows)

      loading_port = parameters.get(
          "loading_port",
          {},
      ).get("raw_value")

      discharging_port = parameters.get(
          "discharging_port",
          {},
      ).get("raw_value")

      route = {
          "origin": loading_port,
          "destination": discharging_port,
          "experimental_route": (
              f"{loading_port} → {discharging_port}"
          ),
          "route_override_note": (
              "Dataset eksperimen berbasis data Aqaba "
              "dengan route override."
          ),
      }

      return {
          "case_id": "CFR-SIM-BONTANG-ECI-001",
          "mode": "simulation",
          "status": "advisory-only",
          "case_type": "voyage_parameter_register",
          "dataset": {
              "file_name": dataset_path.name,
              "sha256": calculate_sha256(dataset_path),
              "source_is_read_only": True,
          },
          "route": route,
          "parameters": parameters,
          "ingest": {
              "batch": "B2-ingest",
              "ingested_at_utc": datetime.now(
                  timezone.utc
              ).isoformat(),
              "numeric_conversion_applied": False,
              "unit_conversion_applied": False,
              "business_decision_applied": False,
          },
      }


def main() -> None:
      repository_root = Path(__file__).resolve().parents[1]
      dataset_path = (
          repository_root
          / "data"
          / "dataset_ready.csv"
      )

      output_path = (
          repository_root
          / "outputs"
          / "case_bontang_eci.json"
      )

      if not dataset_path.exists():
          raise FileNotFoundError(
              f"Dataset tidak ditemukan: {dataset_path}"
          )

      rows = load_rows(dataset_path)
      case = build_case(dataset_path, rows)

      output_path.parent.mkdir(
          parents=True,
          exist_ok=True,
      )

      with output_path.open(
          "w",
          encoding="utf-8",
      ) as file:
          json.dump(
              case,
              file,
              indent=2,
              ensure_ascii=False,
          )

      print(json.dumps(
          {
              "case_id": case["case_id"],
              "mode": case["mode"],
              "status": case["status"],
              "route": case["route"],
              "parameter_count": len(
                  case["parameters"]
              ),
              "output": str(output_path),
          },
          indent=2,
          ensure_ascii=False,
      ))


if __name__ == "__main__":
      main()