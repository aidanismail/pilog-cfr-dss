from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def calculate_sha256(file_path: Path) -> str:
    sha256 = hashlib.sha256()

    with file_path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024**2),
        b""):
            sha256.update(chunk)

    return sha256.hexdigest()


def inspect_csv(file_path: Path)->dict:
    with file_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader=csv.DictReader(file)

        headers=reader.fieldnames or[]
        row_count = 0

        for _ in reader:
            row_count += 1


    return {
        "headers": headers,
        "row_count": row_count,
    }

def build_manifest(dataset_path: Path) -> dict:
    csv_info = inspect_csv(dataset_path)

    return{
          "mode": "simulation",
          "status": "advisory-only",
          "scenario": {
              "name": "Bontang-ECI experimental route",
              "route_origin": "Bontang",
              "route_destination": "ECI",
              "note": (
                  "Dataset berbasis data Aqaba dengan perubahan route"
                  "untuk eksperimen; bukan data produksi PILOG."
              ),
          },
          "dataset": {
              "path": str(dataset_path),
              "file_name": dataset_path.name,
              "size_bytes": dataset_path.stat().st_size,
              "sha256": calculate_sha256(dataset_path),
              "headers": csv_info["headers"],
              "row_count": csv_info["row_count"],
          },
          "run": {
              "executed_at_utc":
              datetime.now(timezone.utc).isoformat(),
              "purpose": "Batch 0 baseline and reproducibility smoke check",
          },
    }


def main() -> None:
      parser = argparse.ArgumentParser(
          description="Batch 0 simulation baseline smoke check"
      )

      parser.add_argument(
          "--dataset",
          default="data/dataset_ready.csv",
          help="Path dataset CSV yang akan diperiksa",
      )

      parser.add_argument(
          "--write-manifest",
          action="store_true",
          help="Simpan manifest ke outputs/simulation_manifest.json",
      )

      args = parser.parse_args()

      repository_root = Path(__file__).resolve().parents[1]
      dataset_path = repository_root / args.dataset

      if not dataset_path.exists():
          raise FileNotFoundError(
              f"Dataset tidak ditemukan: {dataset_path}"
          )

      if dataset_path.suffix.lower() != ".csv":
          raise ValueError(
              f"Batch 0 hanya menerima file CSV: {dataset_path.name}"
          )

      manifest = build_manifest(dataset_path)

      print(json.dumps(manifest, indent=2, ensure_ascii=False))

      if args.write_manifest:
          output_path = repository_root / "outputs" /"simulation_manifest.json"
          output_path.parent.mkdir(parents=True, exist_ok=True)

          with output_path.open("w", encoding="utf-8") as file:
              json.dump(manifest, file, indent=2,
              ensure_ascii=False)

          print(f"\nManifest tersimpan di: {output_path}")


if __name__ == "__main__":
      main()
