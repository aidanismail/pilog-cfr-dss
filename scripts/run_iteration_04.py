"""Run I4 locally; defaults to two tender variants sharing one voyage dataset."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from pilog_cfr_dss.orchestration.iteration_04 import evaluate, persist_run


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulasi I4: tender dan GO/NO GO CFR PILOG")
    parser.add_argument("--case", type=Path)
    parser.add_argument("--output-root", type=Path, default=ROOT / "outputs" / "runs")
    args = parser.parse_args()
    paths = [args.case] if args.case else [ROOT / "data/processed/i4_context.json", ROOT / "data/processed/i4_no_go.json"]
    summaries = []
    for path in paths:
        result = evaluate(path)
        output = persist_run(result, args.output_root)
        summaries.append({"case_id": result["case_id"], "action": result["recommendation"]["action"],
                          "reasons": result["recommendation"]["reason_codes"], "run_dir": str(output)})
    print(json.dumps(summaries, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
