"""Read workbook profiles, preserving physical inputs and source cells."""
from decimal import Decimal, localcontext
import hashlib
from pathlib import Path
import re

from pilog_cfr_dss.calculations.fuel import port_diesel_mt
from pilog_cfr_dss.validation.iteration_04 import number

PROFILE_CELLS = {"dwt_mt": "C16", "speed_knots": "D3", "sea_fo_mt_day": "H6",
                 "sea_do_mt_day": "I6", "running_usd_day": "F44"}
PROFILE_POLICY = {"Handysize": ["1", "40000"], "Handymax": ["40000", "50000"], "Supramax": ["50000", "60000"]}


def read_profiles(path: Path) -> dict:
    from openpyxl import load_workbook
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    workbook = load_workbook(path, read_only=True, data_only=False)
    profiles = []
    try:
        for sheet in workbook:
            if any(sheet[cell].value is None for cell in PROFILE_CELLS.values()):
                continue
            fields = {key: str(number(sheet[cell].value, sheet.title + "!" + cell, Decimal(0))) for key, cell in PROFILE_CELLS.items()}
            dwt = Decimal(fields["dwt_mt"])
            if not 0 < dwt <= 60000:
                continue
            vessel_class = "Handysize" if dwt <= 40000 else "Handymax" if dwt < 50000 else "Supramax"
            formula = str(sheet["J6"].value)
            match = re.fullmatch(r"=([0-9.]+)\*([0-9.]+)\*([0-9.]+)\*24/1000", formula.replace(" ", ""))
            if not match:
                raise ValueError("UNSUPPORTED_PORT_DIESEL_FORMULA:" + sheet.title)
            load, kg, power = (number(value, sheet.title + "!J6") for value in match.groups())
            with localcontext() as precision:
                precision.prec = 40
                fields["port_do_mt_day"] = str(port_diesel_mt(Decimal(1), power, load, kg))
            profiles.append({"profile_id": "ve_" + sheet.title.lower(), "sheet": sheet.title,
                "vessel_class": vessel_class, "vessel_group": "Supramax" if vessel_class == "Supramax" else "Handymax dan lebih kecil",
                "market_family": "Supramax" if vessel_class == "Supramax" else "Handysize",
                "market_class_proxy": vessel_class == "Handymax", "fields": fields,
                "source_reference": "data/raw/Voyage Estimate.xlsx", "source_sha256": digest,
                "source_cells": {**PROFILE_CELLS, "port_do_mt_day": "J6"},
                "source_formula": {"J6": formula},
                "note": "Profil workbook dipakai untuk kasus urea/rute I4; bukan bukti kapal tersedia."
                        + (" Tarif Handymax memakai acuan kelompok kecil Handysize 38k (proxy kelas)." if vessel_class == "Handymax" else "")})
    finally:
        workbook.close()
    if not profiles:
        raise ValueError("NO_SUPPORTED_WORKBOOK_PROFILES")
    return {"profile_version": "VE-PROFILES.1", "source_sha256": digest, "policy": PROFILE_POLICY, "profiles": profiles}
