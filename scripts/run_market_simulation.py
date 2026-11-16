"""Run the active Freight Desk without a UI or any tender fixture."""
import argparse
import csv
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from pilog_cfr_dss.application.freight_desk import default_case,evaluate,export_case,import_case,serializable
from pilog_cfr_dss.sources.fearnpulse import latest_saved,fetch_snapshot,save_runtime_snapshot
from pilog_cfr_dss.reporting.commercial_brief import commercial_brief
ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description="PILOG Freight Desk")
    parser.add_argument("--package",type=Path,help="Replay an exported PILOG-FREIGHT.1 package offline")
    parser.add_argument("--refresh",action="store_true")
    parser.add_argument("--output-root",type=Path,default=ROOT/"outputs/latest_freight")
    args=parser.parse_args()
    if args.package:
        if args.refresh: parser.error("--package replays its own snapshot; do not combine with --refresh")
        case=import_case(args.package.read_bytes())
    else:
        snapshot=fetch_snapshot() if args.refresh else latest_saved(ROOT,ROOT/"outputs/market_cache")
        if snapshot is None: parser.error("No saved market snapshot; use --refresh.")
        if args.refresh:save_runtime_snapshot(snapshot,ROOT/"outputs/market_cache")
        case=default_case(ROOT,snapshot)
    result=evaluate(case)
    folder=args.output_root
    folder.mkdir(parents=True,exist_ok=True)
    (folder/"case.json").write_bytes(export_case(case))
    (folder/"result.json").write_text(json.dumps(serializable(result),ensure_ascii=False,indent=2),encoding="utf-8")
    (folder/"commercial_brief.md").write_text(commercial_brief(result),encoding="utf-8")
    with (folder/"ledger.csv").open("w",encoding="utf-8-sig",newline="") as handle:
        columns=["class","quantity_basis","activity","days","hire_rate","hire_usd","vlsfo_mt","lsmgo_mt","bunker_usd","port_da_usd","other_usd","total_usd"]
        writer=csv.DictWriter(handle,fieldnames=columns);writer.writeheader()
        for family, scenarios in result["classes"].items():
            for label, scenario in scenarios.items():
                for row in scenario["ledger"]:writer.writerow(dict(serializable(row),**{"class":family,"quantity_basis":label}))
    print(json.dumps({"output":str(folder),"recommendation":result["recommendation"],"input_sha256":result["input_sha256"]},ensure_ascii=False))

if __name__=="__main__": main()
