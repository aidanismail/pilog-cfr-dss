"""Capture public Fearnpulse observations and read all supported voyage profiles."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from pilog_cfr_dss.sources.fearnpulse import fetch_snapshot, save_snapshot
from pilog_cfr_dss.sources.voyage_profiles import read_profiles


def main():
    catalog = read_profiles(ROOT / "data/raw/Voyage Estimate.xlsx")
    path = ROOT / "data/processed/vessel_profiles_i4.json"
    path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    snapshot = fetch_snapshot()
    stored = save_snapshot(snapshot, ROOT)
    print(json.dumps({"market_snapshot": str(stored), "fetched_at": snapshot["fetched_at"],
        "report_published_at": snapshot["report_published_at"], "tc_rates": snapshot["tc_rates"],
        "bunkers": snapshot["bunkers"], "profiles": [p["profile_id"] for p in catalog["profiles"]]}, indent=2))


if __name__ == "__main__":
    main()
