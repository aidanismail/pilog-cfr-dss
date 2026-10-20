"""Run both I3 synthetic tender cases, or one with --case. No external writes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pilog_cfr_dss.orchestration.iteration_03 import evaluate, persist_run


def main() -> None:
    parser = argparse.ArgumentParser(description="PILOG CFR DSS — Iterasi 3 tender simulation")
    parser.add_argument("--case", type=Path, help="One I3 case JSON; default runs GO and NO GO fixtures")
    parser.add_argument("--vessel-policy", type=Path, default=ROOT / "data" / "processed" / "vessel_classes.json")
    parser.add_argument("--output-root", type=Path, default=ROOT / "outputs" / "runs")
    args = parser.parse_args()
    cases = [args.case] if args.case else [
        ROOT / "data" / "processed" / "i3_go_urea.json",
        ROOT / "data" / "processed" / "i3_no_go_urea.json",
    ]
    results = []
    for path in cases:
        report = evaluate(path, args.vessel_policy)
        run_dir = persist_run(report, path, args.output_root, args.vessel_policy)
        results.append({"case_id": report["case_id"], "action": report["recommendation"]["action"],
                        "reason_category": report["recommendation"]["reason_category"],
                        "run_dir": str(run_dir)})
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
