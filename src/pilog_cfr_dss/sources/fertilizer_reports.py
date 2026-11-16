"""Product-specific, hash-cached table extraction from supplied Nitrogen PDFs."""
from copy import deepcopy
from datetime import datetime
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
import re
import pypdfium2 as pdfium
from pilog_cfr_dss.models.freight_desk import COMMODITIES
from pilog_cfr_dss.validation.numbers import number

PARSER_VERSION = "NITROGEN.1"
NUMBER = r"\d+(?:\.\d+)?"


def _pages(path):
    doc = pdfium.PdfDocument(str(path))
    pages = []
    try:
        for i in (0, 1):
            page = doc[i]
            text = page.get_textpage()
            try:
                pages.append("\n".join(x.strip() for x in text.get_text_range().splitlines() if x.strip()))
            finally:
                text.close()
                page.close()
    finally:
        doc.close()
    return pages


def _record(path, digest, publisher, date, product, label, low, high, page, basis, kind="commodity", **extra):
    if number(low) <= 0 or number(high) < number(low):
        raise ValueError("INVALID_ASSESSMENT_RANGE")
    return dict(product=product, publisher=publisher, label=label, low=low, high=high,
                basis=basis, unit="USD/MT", observation_date=date, page=page,
                source_file=path.name, source_reference="public/" + path.name,
                source_sha256=digest, evidence="table", kind=kind,
                parser_version=PARSER_VERSION, **extra)


@lru_cache(maxsize=16)
def _read(filename, digest):
    path = Path(filename)
    if sha256(path.read_bytes()).hexdigest() != digest:
        raise ValueError("REPORT_CHANGED_DURING_READ")
    first, second = _pages(path)
    out = []
    if path.name.lower().startswith("argus"):
        match = re.search(r"Issue\s+\S+\s*\|\s*\w+\s+(\d{1,2}\s+\w+\s+\d{4})", first)
        if not match:
            raise ValueError("ARGUS_DATE_NOT_FOUND")
        date = datetime.strptime(match[1], "%d %B %Y").date().isoformat()
        sections = [
            ("urea_granular", "Granular urea - fob bulk", "Sustainable Nitrogen prices", "granular"),
            ("ammonium_sulphate", "Ammonium sulphate – bulk", "Ammonium chloride - bulk", "as_labelled"),
            ("ammonium_chloride", "Ammonium chloride - bulk", "Ammonium nitrate", "bulk"),
        ]
        for product, start, end, grade in sections:
            if start not in second or end not in second.split(start, 1)[1]:
                raise ValueError("ARGUS_SECTION_MISSING:" + product)
            section = second.split(start, 1)[1].split(end, 1)[0]
            for line in section.splitlines():
                m = re.match(r"^(.+?)\s+(" + NUMBER + r")\s*[-–]\s*(" + NUMBER + r")(?:\s|$)", line)
                if not m:
                    continue
                label, lo, hi = m.groups()
                if any(x in label for x in ("$/st", "A$/t", "€/t", "£/t", "weighted average")):
                    continue
                basis = "CFR" if re.search(r"\bcfr\b", label, re.I) else "FCA" if "fca" in label.lower() else "FOB"
                out.append(_record(path, digest, "Argus", date, product, label, lo, hi, 2, basis, grade=grade))
        freight = second.split("Urea freight", 1)[1].split("UAN solution", 1)[0]
        for line in freight.splitlines():
            m = re.match(r"^(.+?)\s+(\d+)\s+(" + NUMBER + r")\s+(" + NUMBER + r")$", line)
            if m:
                # Keep source route label intact; do not infer exact ports.
                out.append(_record(path, digest, "Argus", date, "urea_granular", m[1],
                    m[3], m[4], 2, "Freight", "freight", cargo_kt=m[2], grade="urea"))
    else:
        match = re.search(r"Volume\s+\d+\s*/\s*Issue\s+\d+\s*/\s*(\w+\s+\d{1,2},\s*\d{4})", first)
        if not match:
            raise ValueError("FERTECON_DATE_NOT_FOUND")
        date = datetime.strptime(match[1], "%B %d, %Y").date().isoformat()
        for page, text in enumerate((first, second), 1):
            for line in text.splitlines():
                m = re.match(r"^(.+?)\s+([A-Z0-9]{6,10})\s+(\S+)\s+(\S+)", line)
                if not m:
                    continue
                label, symbol, close, spread = m.groups()
                if "urea" in label.lower() and "(granular)" in label.lower() and "automotive" not in label.lower():
                    product, grade = "urea_granular", "granular"
                elif "ammonium sulfate" in label.lower():
                    product, grade = "ammonium_sulphate", "compacted" if "compact" in label.lower() else "caprolactam"
                else:
                    continue
                if any(x in label for x in ("$/st", "Eur/mt", "Yuan/mt", "GBP/mt")):
                    continue
                values = re.fullmatch("(" + NUMBER + r")[-–](" + NUMBER + ")", spread)
                if values:
                    low, high = values.groups()
                elif re.fullmatch(NUMBER, close) and spread in ("–", "-"):
                    low = high = close
                else:
                    continue
                basis = label.split()[0]
                if basis not in ("FOB", "CFR", "FCA", "CIF"):
                    continue
                out.append(_record(path, digest, "Fertecon", date, product, label,
                                   low, high, page, basis, symbol=symbol, grade=grade))
        freight = second.split("Platts Fertecon dry bulk fertilizer freight assessments", 1)[1].split("Nitrates", 1)[0]
        for line in freight.splitlines():
            m = re.match(r"^(.+?)\s+\((\d+)kt\)\s+(\w+)\s+\S+\s+(" + NUMBER + r")[-–](" + NUMBER + ")", line)
            if m:
                out.append(_record(path, digest, "Fertecon", date, "dry_bulk_fertilizer",
                    m[1], m[4], m[5], 2, "Freight", "freight", cargo_kt=m[2], symbol=m[3], grade="not_stated"))
            else:
                point = re.match(r"^(.+?)\s+\((\d+)kt\)\s+(\w+)\s+(" + NUMBER + r")\s+[-–](?:\s|$)", line)
                if point:
                    out.append(_record(path, digest, "Fertecon", date, "dry_bulk_fertilizer",
                        point[1], point[4], point[4], 2, "Freight", "freight",
                        cargo_kt=point[2], symbol=point[3], grade="not_stated"))
    return out


def read_assessments(root):
    """Latest parseable edition per publisher; failures remain explicit."""
    records, errors = [], []
    for prefix in ("Argus", "Fertecon"):
        candidates = []
        for path in (Path(root) / "public").glob(prefix + "*Nitrogen*.pdf"):
            try:
                items = _read(str(path.resolve()), sha256(path.read_bytes()).hexdigest())
                if not items:
                    raise ValueError("NO_ASSESSMENTS")
                candidates.append(items)
            except (ValueError, OSError, pdfium.PdfiumError, IndexError) as error:
                errors.append({"source": path.name, "error": str(error)})
        if candidates:
            date = max(items[0]["observation_date"] for items in candidates)
            latest = [items for items in candidates if items[0]["observation_date"] == date]
            if len({items[0]["source_sha256"] for items in latest}) != 1:
                errors.append({"source": prefix, "error": "AMBIGUOUS_LATEST_EDITION"})
            else:
                records.extend(latest[0])
    return {"parser_version": PARSER_VERSION, "records": deepcopy(records), "errors": errors}


def for_product(snapshot, product):
    if product not in COMMODITIES:
        raise ValueError("UNSUPPORTED_COMMODITY")
    return [deepcopy(r) for r in snapshot["records"] if r["kind"] == "commodity" and r["product"] == product]


def destination_context(snapshot, product, country):
    """Select labelled country/region evidence without converting FOB into CFR."""
    records = for_product(snapshot, product)
    regional = {
        **{name: ("Southeast Asia", "SE Asia") for name in
           ("Indonesia", "Malaysia", "Singapore", "Brunei", "Vietnam", "Thailand", "Philippines")},
        **{name: ("North Africa",) for name in ("Libya", "Algeria", "Egypt", "Morocco", "Tunisia")},
    }
    aliases = {"United States": ("US Gulf", "NOLA"), "South Korea": ("Korea",)}
    names = aliases.get(country, (country,))
    selected = []
    for publisher in sorted({row["publisher"] for row in records}):
        pool = [row for row in records if row["publisher"] == publisher]
        exact = [row for row in pool if row["basis"] == "CFR"
                 and any(re.search(r"\b" + re.escape(name) + r"\b", row["label"], re.I) for name in names)]
        region = [row for row in pool if any(name.casefold() in row["label"].casefold()
                  for name in regional.get(country, ()))]
        cfr = [row for row in region if row["basis"] == "CFR"]
        choices = exact or cfr or region or pool[:2]
        scope = ("CFR negara tujuan; bukan quote terminal" if exact else
                 "CFR regional" if cfr else "Konteks regional sesuai basis sumber" if region else
                 "Wilayah lain; bukan harga CFR tujuan")
        selected.extend(dict(row, context_scope=scope) for row in choices)
    return selected
