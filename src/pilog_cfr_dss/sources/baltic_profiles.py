"""Verify the configured vessel profiles against Baltic's public benchmarks."""
from datetime import datetime, timezone
from hashlib import sha256
from html.parser import HTMLParser
from pathlib import Path
import json
import re
import requests

URL = "https://www.balticexchange.com/en/data-services/market-information0/dry-services.html"
SNAPSHOT = Path(__file__).resolve().parents[3]/'data/processed/baltic_vessel_benchmarks.json'


def read_snapshot():
    data=json.loads(SNAPSHOT.read_text(encoding='utf-8'))
    if set(data['profiles']) != {'Handysize','Supramax'}:
        raise ValueError('INVALID_BALTIC_SNAPSHOT')
    return data


class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def verify_profiles(html, profiles):
    parser = _Text()
    parser.feed(html)
    text = " ".join(" ".join(parser.parts).split())
    sections = {
        "Supramax": ("Baltic Supramax vessel for Timecharter routes", "Handysize Index"),
        "Handysize": ("Baltic Handysize 38 vessel for Timecharter routes", "Sale & Purchase"),
    }
    for family, (start, end) in sections.items():
        _, marker, after = text.partition(start)
        block, stop, _ = after.partition(end)
        if not marker or not stop:
            raise ValueError("BALTIC_PROFILE_SECTION_NOT_FOUND:" + family)
        spec = profiles[family]
        dwt = rf"(?<![\d,]){int(spec['dwt_mt']):,}\s*mt\s*dwt"
        draft = rf"{re.escape(spec['summer_draft_m'])}\s*m\s+SSW"
        tpc = rf"\bTPC\s+{re.escape(spec['tpc_mt_cm'])}(?![\d.])"
        grain = rf"{int(spec['grain_m3']):,}\s*cbm"
        speeds = rf"{re.escape(spec['speed_knots'])}\s+knots on\s+{re.escape(spec['sea_fo_mt_day'])}\s*mt"
        checks = [dwt, draft, tpc]
        if family == "Supramax":
            checks.extend([rf"\bGRAIN\s*:\s*{grain}",
                           rf"{speeds}\s+laden[^.]*\.\s*Marine Fuel Oil,\s*no Marine Gas Oil at sea"])
            if spec["sea_do_mt_day"] != "0":
                raise ValueError("BALTIC_BENCHMARK_CHANGED:" + family)
        else:
            checks.extend([rf"{grain}\s+grain",
                           rf"{speeds}\s+IFO\s*\(380 CST\)\s+laden/[^+]*\+\s*{re.escape(spec['sea_do_mt_day'])}\s+MDO at sea"])
        if not all(re.search(check, block, re.IGNORECASE) for check in checks):
            raise ValueError("BALTIC_BENCHMARK_CHANGED:" + family)


def verify_benchmarks():
    response = requests.get(URL, timeout=8)
    response.raise_for_status()
    if len(response.content) > 2_000_000 or "text/html" not in response.headers.get("Content-Type", ""):
        raise ValueError("BALTIC_INVALID_DOCUMENT")
    verify_profiles(response.text, read_snapshot()["profiles"])
    return {"url": URL, "checked_at": datetime.now(timezone.utc).isoformat(),
            "sha256": sha256(response.content).hexdigest(), "status": "verified"}
