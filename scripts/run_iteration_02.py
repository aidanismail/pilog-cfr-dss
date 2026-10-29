"""Run a local advisory-only Iteration 2 simulation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pilog_cfr_dss.orchestration.pipeline import evaluate, persist_run


def main() -> None:
    parser = argparse.ArgumentParser(description="PILOG CFR DSS — Simulation Iteration 2")
    parser.add_argument("--dataset", type=Path, default=ROOT / "data" / "processed" / "dataset_ready.csv")
    parser.add_argument("--catalog", type=Path, default=ROOT / "data" / "processed" / "variable_catalog.csv")
    parser.add_argument("--manual", type=Path, default=ROOT / "data" / "processed" / "iteration_02_pre_offer_simulation.json")
    parser.add_argument("--vessel-policy", type=Path, default=ROOT / "data" / "processed" / "vessel_classes.json")
    parser.add_argument("--output-root", type=Path, default=ROOT / "outputs" / "runs")
    args = parser.parse_args()
    report = evaluate(args.dataset, args.catalog, args.manual, args.vessel_policy)
    output = persist_run(report, args.output_root, {
        "dataset": args.dataset, "catalog": args.catalog, "manual": args.manual,
        "vessel_policy": args.vessel_policy,
    })
    print(json.dumps({"run_dir": str(output), "quality": report["quality"]["status"], "gate_1": report["gate_1"]["outcome"], "gate_2": report["gate_2"]["outcome"], "action": report["recommendation"]["action"]}, indent=2))


if __name__ == "__main__":
    main()
