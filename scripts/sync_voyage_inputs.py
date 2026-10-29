"""Refresh derived voyage/profile catalogs from Excel, without a market fetch."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from pilog_cfr_dss.application.market_case import catalog, voyage_catalog


def main():
    for filename, content in (("vessel_profiles_i4.json", catalog(ROOT)),
                              ("voyage_estimates_i5.json", voyage_catalog(ROOT))):
        path = ROOT / "data/processed" / filename
        path.write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
