"""Optional, versioned transaction facts and stress inputs for a freight case."""
from datetime import date, timezone
from decimal import Decimal

from pilog_cfr_dss.validation.numbers import number, timestamp


VERSION = "1"
PARTIES = {"unknown": "Belum diketahui", "PI": "PI", "PILOG": "PILOG", "other": "Pihak lain"}
STATUSES = {"unknown": "Belum diketahui", "indicative": "Indikatif", "open": "Belum dikunci", "binding": "Mengikat"}
BASES = {"unknown": "Belum diketahui", "fixed": "Tetap", "adjustable": "Dapat disesuaikan"}
AGREEMENTS = {"cfr": "Penjualan CFR PI ke buyer", "freight": "Jasa freight PILOG ke PI", "charter": "Sewa kapal PILOG"}
STRESSES = {
    "physical_freight": ("Harga freight fisik PI", "USD/MT"),
    "hire": ("Hire kapal", "USD/hari"),
    "selling_freight": ("Tarif jual jasa PILOG", "USD/MT"),
    "VLSFO": ("Harga VLSFO", "USD/MT"),
    "LSMGO": ("Harga LSMGO", "USD/MT"),
    "load_wait": ("Tambahan waktu tunggu muat", "hari"),
    "discharge_wait": ("Tambahan waktu tunggu bongkar", "hari"),
    "cargo": ("Muatan baru", "MT"),
    "draft": ("Batas draft bongkar baru", "m"),
}


def voyage_scope(case):
    return {"ports": [[case["ports"][side][key] for key in ("name", "country")]
                      for side in ("load", "discharge")],
            "commodity": case["commodity"], "cargo_mt": str(number(case["cargo_mt"]).normalize()),
            "start_at": timestamp(case["start_at"]).astimezone(timezone.utc).isoformat()}


def risk_input(case):
    """Read and validate the extension. An absent extension preserves old cases."""
    if "risk_assessment" not in case:
        return None
    data = case["risk_assessment"]
    if not isinstance(data, dict) or data.get("version") != VERSION:
        raise ValueError("Versi status transaksi tidak didukung.")
    def profile(key):
        value = data.get(key, {})
        if not isinstance(value, dict):
            raise ValueError(f"Format {key} tidak valid.")
        return value

    def text(item, field):
        value = item.get(field, "")
        if not isinstance(value, str) or len(value) > 300:
            raise ValueError(f"Isi {field} dengan teks maksimal 300 karakter.")
        return value.strip()

    def agreement(item):
        if not isinstance(item, dict):
            raise ValueError("Format komitmen tidak valid.")
        status, basis = item.get("status", "unknown"), item.get("basis", "unknown")
        if not isinstance(status, str) or not isinstance(basis, str) or status not in STATUSES or basis not in BASES:
            raise ValueError("Status atau dasar harga transaksi tidak valid.")
        coverage = optional_number(item, "coverage_percent", Decimal(0))
        if coverage is not None and coverage > 100:
            raise ValueError("Cakupan komitmen maksimal 100%.")
        dates = {key: text(item, key) for key in ("agreed_on", "valid_until")}
        for value in filter(None, dates.values()):
            date.fromisoformat(value)
        if dates["agreed_on"] and dates["valid_until"] and dates["agreed_on"] > dates["valid_until"]:
            raise ValueError("Tanggal berlaku mendahului tanggal kesepakatan.")
        return {"status": status, "basis": basis, "coverage": coverage,
                "rate": optional_number(item, "rate", Decimal(0)), "evidence": text(item, "evidence"), **dates}

    raw_agreements = profile("commitments")
    commitments = {key: agreement(raw_agreements.get(key, {})) for key in AGREEMENTS}
    raw_charter = raw_agreements.get("charter", {})
    charter_class = raw_charter.get("vessel_class")
    if charter_class is not None and (not isinstance(charter_class, str) or charter_class not in case["profiles"]):
        raise ValueError("Kelas kapal pada komitmen sewa tidak valid.")
    comparable = raw_charter.get("quote_comparable", False)
    if not isinstance(comparable, bool):
        raise ValueError("Status kesesuaian quotation tidak valid.")
    nominated = data.get("vessel_nominated")
    if nominated is not None and not isinstance(nominated, bool):
        raise ValueError("Status nominasi kapal tidak valid.")
    costs = {}
    for key in ("VLSFO", "LSMGO", "port_delay"):
        item = profile(key)
        payer = item.get("payer", "unknown")
        if not isinstance(payer, str) or payer not in PARTIES:
            raise ValueError("Pihak penanggung biaya tidak valid.")
        costs[key] = {**agreement(item), "payer": payer}
    raw_stresses = profile("stresses")
    if unknown := raw_stresses.keys() - STRESSES.keys():
        raise ValueError(f"Skenario risiko tidak dikenali: {', '.join(sorted(unknown))}.")
    stresses = {key: optional_number(raw_stresses, key, Decimal(0) if key in
                ("load_wait", "discharge_wait", "cargo", "draft") else None) for key in raw_stresses}
    if any(stresses.get(key) == 0 for key in ("cargo", "draft")):
        raise ValueError("Muatan dan batas draft skenario harus lebih dari nol.")
    demurrage = profile("demurrage")
    claims = {key: optional_number(demurrage, key, Decimal(0)) for key in ("payable_usd", "recoverable_usd")}
    claims.update(evidence=text(demurrage, "evidence"), basis=text(demurrage, "basis"))
    recurring = data.get("recurring_program", False)
    if not isinstance(recurring, bool):
        raise ValueError("Status program berulang tidak valid.")
    return {"version": VERSION, "commitments": commitments, "charter_class": charter_class,
            "quote_comparable": comparable,
            "vessel_nominated": nominated, **costs, "stresses": stresses, "demurrage": claims,
            "fx_evidence": text(data, "fx_evidence"), "liability_evidence": text(data, "liability_evidence"),
            "recurring_program": recurring, "scope_matches": data.get("scope") == voyage_scope(case)}


def optional_number(data, key, minimum=None):
    value = data.get(key)
    return None if value is None or value == "" else number(value, key, minimum)
