"""Refresh source catalogs from the unchanged workbook, without market requests."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from pilog_cfr_dss.sources.voyage_profiles import read_profiles
from pilog_cfr_dss.sources.voyage_estimates import read_voyages

def main():
    for name,reader in (("vessel_profiles.json",lambda:read_profiles(ROOT/"data/raw/Voyage Estimate.xlsx")),
                        ("voyage_estimates_i5.json",lambda:read_voyages(ROOT/"data/raw/Voyage Estimate.xlsx",None))):
        path=ROOT/"data/processed"/name
        path.write_text(json.dumps(reader(),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print(path.relative_to(ROOT))
if __name__=="__main__":main()
