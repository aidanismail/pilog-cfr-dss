"""Fetch public market observations; PDFs are read from the repository."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from pilog_cfr_dss.sources.fearnpulse import fetch_snapshot,save_runtime_snapshot
from pilog_cfr_dss.sources.fertilizer_reports import read_assessments

def main():
    snapshot=fetch_snapshot()
    save_runtime_snapshot(snapshot,ROOT/"outputs/market_cache")
    reports=read_assessments(ROOT)
    print(json.dumps({"fetched_at":snapshot["fetched_at"],"tc_rates":snapshot["tc_rates"],
        "bunkers":snapshot["bunkers"],"report_rows":len(reports["records"]),"report_errors":reports["errors"]},indent=2))
if __name__=="__main__":main()
