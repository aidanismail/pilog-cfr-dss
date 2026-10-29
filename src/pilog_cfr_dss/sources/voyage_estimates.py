"""Read demo voyage inputs separately from workbook vessel specifications."""
import hashlib
from pathlib import Path
import re
from decimal import Decimal, localcontext

from pilog_cfr_dss.calculations.voyage_04 import port_expenses_total
from pilog_cfr_dss.sources.od_distance import read_distance
from pilog_cfr_dss.validation.iteration_04 import number

SOURCE = "data/raw/Voyage Estimate.xlsx"


def read_voyages(path: Path, od_path: Path) -> dict:
    from openpyxl import load_workbook
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    workbook = load_workbook(path, read_only=True, data_only=False)
    voyages = []
    try:
        for sheet in workbook:
            route = str(sheet["B9"].value or "").split(" - ")
            if len(route) != 2 or not all(p.strip() for p in route):
                raise ValueError("INVALID_VOYAGE_ROUTE:" + sheet.title)
            origin, destination = (p.strip().title() for p in route)
            if any(number(sheet[c].value, sheet.title + "!" + c, Decimal(0)) != 0 for c in ("G10", "H10")):
                raise ValueError("UNSUPPORTED_RETURN_LEG:" + sheet.title)
            if str(sheet["B5"].value).splitlines()[0].strip() != "UREA GRANULAR BULK":
                raise ValueError("UNSUPPORTED_VOYAGE_PRODUCT:" + sheet.title)
            cargo = number(sheet["D20"].value, sheet.title + "!D20")
            if cargo <= 0:
                raise ValueError("INVALID_VOYAGE_CARGO")
            revenue_quantity = sheet["B41"].value
            if revenue_quantity != "=D20" and number(revenue_quantity, sheet.title + "!B41") != cargo:
                raise ValueError("CARGO_REVENUE_QUANTITY_MISMATCH")
            distance = read_distance(od_path, origin, destination, "UREA GRANULAR BULK")
            if number(sheet["F3"].value, sheet.title + "!F3") != Decimal(distance["value"]):
                raise ValueError("WORKBOOK_OD_DISTANCE_MISMATCH:" + sheet.title)
            fields = {"loading_port": origin, "discharging_port": destination,
                      "cargo_description": "UREA GRANULAR BULK", "cargo_category": "dry_bulk",
                      "cargo_mt": str(cargo), "voyage_boundary": "laden_only"}
            cells = {"loading_port": "B9", "discharging_port": "B9", "cargo_description": "B5",
                     "cargo_category": "B5", "cargo_mt": "D20/B41", "voyage_boundary": "B10/H10"}
            for key, cell in (("loading_rate_mt_day", "D12"), ("discharge_rate_mt_day", "F12")):
                match = re.fullmatch(r"=D20/([0-9]+(?:\.[0-9]+)?)", str(sheet[cell].value).replace(" ", ""))
                if not match or number(match[1], cell) <= 0:
                    raise ValueError("UNSUPPORTED_HANDLING_FORMULA:" + sheet.title + "!" + cell)
                fields[key], cells[key] = match[1], cell
            waiting = number(sheet["H11"].value, sheet.title + "!H11", Decimal(0))
            fields["waiting_days"], cells["waiting_days"] = str(waiting), "H11"
            with localcontext() as precision:
                precision.prec = 40
                total = port_expenses_total(number(sheet[f"I{row}"].value, sheet.title + f"!I{row}", Decimal(0))
                                            for row in range(33, 38))
            fields["port_other_total_usd"], cells["port_other_total_usd"] = str(total), "I33:I37"
            voyage_id = re.sub(r"[^a-z0-9]+", "_", (origin + "_" + destination).casefold()).strip("_")
            voyages.append({"voyage_id": voyage_id, "label": origin + " → " + destination,
                            "sheet": sheet.title, "fields": fields, "source_cells": cells,
                            "source_reference": SOURCE, "source_sha256": digest,
                            "distance_reference": distance, "source_status": "simulation_only_workbook_case",
                            "note": "Kasus urea contoh; muatan, handling, waktu tunggu dan biaya pelabuhan adalah asumsi demo, bukan data aktual terminal."})
    finally:
        workbook.close()
    if not voyages or len({v["voyage_id"] for v in voyages}) != len(voyages):
        raise ValueError("EMPTY_OR_DUPLICATE_VOYAGES")
    return {"voyage_version": "VE-VOYAGES.1", "source_sha256": digest, "voyages": voyages}
