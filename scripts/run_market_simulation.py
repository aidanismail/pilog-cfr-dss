"""Active Fearnpulse + workbook case; the earlier CLI remains a replay tool."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from pilog_cfr_dss.sources.fearnpulse import latest_saved, fetch_snapshot, save_snapshot
from pilog_cfr_dss.application.market_case import demo_case, catalog


def main():
    parser = argparse.ArgumentParser(description="Fearnpulse + workbook, kasus GO/NO GO")
    parser.add_argument("--profile", choices=[p["profile_id"] for p in catalog(ROOT)["profiles"]], default="ve_sheet1")
    parser.add_argument("--case", choices=["go", "no-go", "no-go-floor", "no-go-economics", "both", "all"], default="all")
    parser.add_argument("--refresh", action="store_true", help="Ambil snapshot pasar baru sebelum membuat kasus")
    parser.add_argument("--output-root", type=Path, default=ROOT / "outputs")
    args = parser.parse_args()
    snapshot = latest_saved(ROOT)
    if args.refresh:
        snapshot = fetch_snapshot(); save_snapshot(snapshot, ROOT)
    if snapshot is None:
        parser.error("Belum ada snapshot. Jalankan scripts/refresh_market_inputs.py atau --refresh.")
    results = []
    kinds = ["go", "no-go-floor", "no-go-economics"] if args.case == "all" else ["go", "no-go-floor"] if args.case == "both" else ["no-go-floor" if args.case == "no-go" else args.case]
    anchor = demo_case(ROOT, snapshot, args.output_root / "ui_cases", "go", args.profile)
    for kind in kinds:
        case = demo_case(ROOT, snapshot, args.output_root / "ui_cases", kind, args.profile, base_case=anchor)
        report = case.evaluate(args.output_root / "ui_cases", args.output_root / "runs")
        results.append({"example": kind, "action": report["recommendation"]["action"], "gate_a": report["recommendation"]["gate_a"],
            "gate_b": report["recommendation"]["gate_b"], "profile": args.profile,
            "market_snapshot": snapshot["snapshot_id"], "freight_usd_mt": report["pricing"]["freight_tender_usd_mt"],
            "fixed_at": report["pricing"]["fixed_at"], "net_pilog_usd": report["baseline"]["contribution_usd"], "run_dir": str(case.run_dir)})
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
