"""Versioned input catalog. Factors transcribed from supplied CMN screenshots."""
SCHEMA = "PILOG-FREIGHT.1"
FORMULA = "FD.1"
COMMODITIES = {
    "urea_granular": "Urea granular",
    "ammonium_sulphate": "Ammonium sulphate / ZA",
    "ammonium_chloride": "Ammonium chloride",
}
# Exclusions are local weekday/minute boundaries; Monday=0, Sunday=6.
# Factors are source observations, not universal contractual coefficients.
_ROWS = [
    ("CQD1", "Customary Quick Despatch SHINC", "1", None),
    ("FHEX1", "Friday & holidays excluded", "1.1667", (4, 0, 5, 0)),
    ("FHEX2", "Wednesday 17:00–Saturday 08:00 excluded", "1.6", (2, 1020, 5, 480)),
    ("FHEX3", "Friday 12:00–Sunday 08:00 excluded", "1.3548", (4, 720, 6, 480)),
    ("FHEX4", "Friday 12:00–Monday 08:00 excluded", "1.68", (4, 720, 7, 480)),
    ("FHINC", "Friday & holidays included", "1", None),
    ("SHEX0", "Sunday & holidays excluded", "1.1667", (6, 0, 7, 0)),
    ("SHEX1", "Saturday 12:00–Sunday 24:00 excluded", "1.2727", (5, 720, 7, 0)),
    ("SHEX10", "Saturday 18:00–Monday 08:00 excluded", "1.2923", (5, 1080, 7, 480)),
    ("SHEX2", "Saturday 12:00–Monday 08:00 excluded", "1.3548", (5, 720, 7, 480)),
    ("SHEX3", "Friday 24:00–Sunday 24:00 excluded", "1.4", (5, 0, 7, 0)),
    ("SHEX4", "Friday 17:00–Sunday 24:00 excluded", "1.4867", (4, 1020, 7, 0)),
    ("SHEX5", "Friday 24:00–Monday 08:00 excluded", "1.5", (5, 0, 7, 480)),
    ("SHEX6", "Friday 17:00–Monday 08:00 excluded", "1.6", (4, 1020, 7, 480)),
    ("SHEX7", "Friday 20:00–Monday 08:00 excluded", "1.55", (4, 1200, 7, 480)),
    ("SHEX8", "Saturday 14:00–Sunday 24:00 excluded", "1.3333", (5, 840, 7, 0)),
    ("SHEX9", "Saturday 17:00–Monday 08:00 excluded", "1.3023", (5, 1020, 7, 480)),
    ("SHINC", "Sunday & holidays included", "1", None),
    ("SSINCHEX", "Saturday & Sunday included; holidays excluded", "1.04", None),
    ("THEX", "Thursday 12:00–Sunday 08:00 excluded", "1.68", (3, 720, 6, 480)),
    ("THEX1", "Thursday 16:00–Sunday 08:00 excluded", "1.615", (3, 960, 6, 480)),
    ("THEX2", "Thursday 17:00–Saturday 08:00 excluded", "1.3", (3, 1020, 5, 480)),
    ("THEX3", "Thursday 12:00–Saturday 08:00 excluded", "1.35", (3, 720, 5, 480)),
]
TERMS = {
    code: {"label": label, "factor": factor, "excluded_interval": interval,
           "source": ("User confirmation 2026-11-13 :: THEX3 Thu 12:00–Sat 08:00 EXCL 1.35"
                      if code == "THEX3" else
                      "docs/UI References/" + ("terms_1.jpeg" if i < 11 else "term_2.jpeg"))}
    for i, (code, label, factor, interval) in enumerate(_ROWS)
}

TERMS_VERSION = "CMN-TERMS.2"
TERMS_EVIDENCE_SHA256 = {'terms_1.jpeg': '3ca5e0804d24459ff15d5c3a269eee707ce0eaf4790028c75541f5a39c79169d', 'term_2.jpeg': 'd031abcadf2e06013dbcb812566b615820d7916e0c9db4fce4205d08faebd4d9'}
for term in TERMS.values():
    term["source_sha256"] = TERMS_EVIDENCE_SHA256.get(term["source"].rsplit("/",1)[-1])


def terms_catalog(version):
    if version == TERMS_VERSION:
        return TERMS
    if version == "CMN-TERMS.1":
        return {key: value for key, value in TERMS.items() if key != "THEX3"}
    raise ValueError("FORMULA_OR_TERMS_VERSION_MISMATCH")
