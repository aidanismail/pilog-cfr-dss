"""I/O and case snapshots. No business arithmetic and no tender dependency."""
from copy import deepcopy
from datetime import date, datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from uuid import uuid4
from pilog_cfr_dss.models.freight_desk import SCHEMA, FORMULA, TERMS, TERMS_VERSION
from pilog_cfr_dss.calculations.freight_desk import calculate, freight_delta
from pilog_cfr_dss.calculations.risk import assess
from pilog_cfr_dss.models.risk import risk_input
from pilog_cfr_dss.sources.baltic_profiles import read_snapshot
from pilog_cfr_dss.sources.voyage_profiles import read_profiles
from pilog_cfr_dss.sources.voyage_estimates import read_voyages
from pilog_cfr_dss.sources.route_distance import distance
from pilog_cfr_dss.sources.fertilizer_reports import read_assessments
from pilog_cfr_dss.decisions.freight_desk import recommend
from pilog_cfr_dss.validation.numbers import unique_object
from pilog_cfr_dss.sources.kobc import select_assessment


def serializable(value):
    from decimal import Decimal
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {k: serializable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [serializable(v) for v in value]
    return value


def canonical(value):
    return json.dumps(serializable(value), sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def digest(value):
    return sha256(canonical(value).encode("utf-8")).hexdigest()


def sync_fearnpulse(case, market):
    case["market_snapshot"] = deepcopy(market)
    for grade, key in (("VLSFO", "fo_price_usd_mt"), ("LSMGO", "do_price_usd_mt")):
        path = f"fuel.{grade}.value"
        if case["sources"].get(path, {}).get("status") == "manual_override":
            continue
        item = deepcopy(market["bunkers"][key])
        item.update(requested_grade=grade, proxy=True, original_value=item["value"])
        case["fuel"][grade] = item
        case["sources"][path] = {
            "original": item["value"], "source": item["source_reference"],
            "status": "market_proxy", "observation_date": item["source_observed_on"],
        }


def default_case(root: Path, market: dict):
    if not market:
        raise ValueError("MARKET_SNAPSHOT_REQUIRED")
    workbook = root / "data/raw/Voyage Estimate.xlsx"
    voyage = read_voyages(workbook, None)["voyages"][0]
    vessels = read_profiles(workbook)["profiles"]
    baltic = read_snapshot()
    profiles = {}
    provenance = {}
    for family, code in (("Handysize", "HS38"), ("Supramax", "SUP58")):
        supplemental = next(p for p in vessels if p["profile_code"] == code)
        spec = baltic["profiles"][family]
        fields = {"dwt_mt": spec["dwt_mt"], "speed_knots": spec["speed_knots"],
                  "sea_vlsfo_mt_day": spec["sea_fo_mt_day"], "sea_lsmgo_mt_day": spec["sea_do_mt_day"],
                  "summer_draft_m": spec["summer_draft_m"], "grain_m3": spec["grain_m3"],
                  "tpc_mt_cm": spec["tpc_mt_cm"],
                  "port_vlsfo_mt_day": "0",
                  "port_lsmgo_mt_day": supplemental["fields"]["port_do_mt_day"],
                  "bunkers_allowance_mt": supplemental["fields"]["bunkers_allowance_mt"],
                  "constants_allowance_mt": supplemental["fields"]["constants_allowance_mt"]}
        fields["hire_usd_day"] = "13000"
        profiles[family] = fields
        for key in fields:
            ref = ("Approved planning default; enter quote if market unavailable" if key == "hire_usd_day" else
                   "Approved model default: VLSFO port consumption 0" if key == "port_vlsfo_mt_day" else
                   supplemental["source_reference"] + " :: " + supplemental["sheet"] if key in (
                       "port_lsmgo_mt_day", "bunkers_allowance_mt", "constants_allowance_mt") else
                   baltic["source_url"] + " :: PDF page " + str(spec["page"]))
            provenance["profiles." + family + "." + key] = {"source": ref,
                "status": "default_assumption" if key in ("port_vlsfo_mt_day", "hire_usd_day") else
                          "workbook_assumption" if key in ("port_lsmgo_mt_day", "bunkers_allowance_mt", "constants_allowance_mt") else "source_specification",
                "original": fields[key], "sha256": supplemental["source_sha256"] if "workbook" in ref.lower() or "Estimate.xlsx" in ref else None}
    vf = voyage["fields"]
    port_defaults = {}
    for side, name_key, rate_key in (("load", "loading_port", "loading_rate_mt_day"),
                                     ("discharge", "discharging_port", "discharge_rate_mt_day")):
        port_defaults[side] = {"name": vf[name_key], "country": "",
            "rate_mt_day": vf[rate_key], "terms": "SHINC", "time_basis": "factor",
            "draft_limit_m": None, "port_da_usd": "100000", "allowance_days": "0", "time_margin_percent": "25",
            "waiting_days": vf["waiting_days"] if side == "load" else "0",
            "calendar": {"timezone": "UTC", "holidays": []}}
    # Countries are read from the supplied port catalog, never inferred by route.
    from pilog_cfr_dss.sources.route_distance import ports
    catalog = ports(root / "data/raw/Ports.xlsx")
    for port in port_defaults.values():
        matches = [country for name, country in catalog if name.casefold() == port["name"].casefold()]
        if len(matches) != 1:
            raise ValueError("DEFAULT_PORT_NOT_UNIQUE")
        port["country"] = matches[0]
    case = {"schema": SCHEMA, "formula_version": FORMULA, "terms_version": TERMS_VERSION,
        "terms_snapshot": serializable(deepcopy(TERMS)),
        "case_id": "fd_" + uuid4().hex, "currency": "USD",
        "commodity": "urea_granular", "cargo_mt": vf["cargo_mt"],
        "sf_unit": "m3/MT", "stowage_factor_m3_mt": "1.315", "tolerance_percent": "10",
        "commission_fraction": "0", "hire_usd_day": "13000", "bunker_delay_days": "0",
        "selling_freight_usd_mt": None, "other_costs": [], "ports": port_defaults,
        "start_at": datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat(),
        "distance_nm": None, "profiles": profiles, "sources": provenance,
        "report_snapshot": read_assessments(root),
        "workbook_source": voyage, "profile_source": baltic,
        "fuel": {}}
    sync_fearnpulse(case, market)
    for key, value in case.items():
        if isinstance(value, (str, type(None))) and key not in ("schema", "case_id"):
            provenance[key] = {"original": value, "source": "Approved case default", "status": "default_assumption"}
    provenance["cargo_mt"] = {"original": case["cargo_mt"],
        "source": voyage["source_reference"] + " :: " + voyage["sheet"],
        "status": "workbook_assumption", "sha256": voyage["source_sha256"]}
    provenance["hire_usd_day"] = {"original": "13000", "source": "Legacy FD.1/FD.2 only; FD.3 uses hire per class", "status": "legacy_unused"}
    for side, port in port_defaults.items():
        for key in ("rate_mt_day", "waiting_days", "terms", "port_da_usd", "allowance_days", "draft_limit_m", "time_margin_percent"):
            provenance["ports." + side + "." + key] = {"original": port[key], "source":
                voyage["source_reference"] + " :: " + voyage["sheet"] if key == "rate_mt_day" or (key == "waiting_days" and side == "load")
                else "Approved planning default; port draft unknown" if key == "draft_limit_m" else "Approved planning default",
                "status": "workbook_assumption" if key == "rate_mt_day" or (key == "waiting_days" and side == "load") else "default_assumption"}
    update_route(case, root)
    return case


def sync_kobc(case, incoming, today):
    """Refresh eligible benchmarks while preserving user-entered hire."""
    previous = case.get("kobc_snapshot", {"classes": {}, "errors": {}})
    merged = {"provider": "KOBC", "as_of": today.isoformat(),
              "fetched_at": incoming.get("fetched_at", previous.get("fetched_at")),
              "classes": deepcopy(previous.get("classes", {})),
              "errors": deepcopy(incoming.get("errors", {}))}
    for family, quote in incoming.get("classes", {}).items():
        old = merged["classes"].get(family)
        if not old or quote["observed_on"] >= old.get("observed_on", ""):
            if not old or (quote["observed_on"], quote["values"]) != (old.get("observed_on"), old.get("values")):
                merged["classes"][family] = deepcopy(quote)
    case["kobc_snapshot"] = merged
    changed = False
    for family, profile in case["profiles"].items():
        if "hire_usd_day" not in profile:
            continue  # legacy packages preserve their single hire input
        path = "profiles." + family + ".hire_usd_day"
        source = case["sources"].get(path, {})
        if source.get("status") == "manual_override":
            continue
        quote = select_assessment(merged, family, case["ports"]["load"], case["ports"]["discharge"], today)
        if quote:
            old_value, old_code = profile["hire_usd_day"], source.get("benchmark_code")
            profile["hire_usd_day"] = quote["value"]
            case["sources"][path] = {"status": "market_benchmark", "source": quote["source_url"],
                "benchmark_code": quote["code"], "description": quote["description"], "scope": quote["scope"],
                "observed_on": quote["observed_on"], "fetched_at": quote["fetched_at"],
                "benchmark_dwt_mt": quote["benchmark_dwt_mt"], "commission_basis": quote["commission_basis"],
                "unit": "USD/day", "original": quote["value"]}
            changed |= old_value != quote["value"] or old_code != quote["code"]
        elif source.get("status") != "unavailable" and family in merged["classes"]:
            profile["hire_usd_day"] = None
            case["sources"][path] = {"status": "unavailable", "source": "KOBC >7 hari atau tidak tersedia; isi manual"}
            changed = True
    return changed


def reselect_saved_kobc(case):
    snapshot = case.get("kobc_snapshot", {})
    if not snapshot.get("as_of"):
        return False
    return sync_kobc(case, {"classes": {}, "errors": snapshot.get("errors", {})},
                     date.fromisoformat(snapshot["as_of"]))


def update_route(case, root):
    load, discharge = case["ports"]["load"], case["ports"]["discharge"]
    try:
        ref = distance((load["name"], load["country"]), (discharge["name"], discharge["country"]),
                       catalog=root / "data/processed/port_locations_unlocode.json")
        case["distance_nm"] = ref["value"]
        case["sources"]["distance_nm"] = ref
    except ValueError:
        case["distance_nm"] = None
        case["sources"]["distance_nm"] = {"status": "unavailable", "source": "Manual distance required"}


def override(case, path, value):
    keys = path.split(".")
    target = case
    for key in keys[:-1]:
        target = target[key]
    if target[keys[-1]] == value:
        return False
    reference = deepcopy(case["sources"].get(path, {"original": deepcopy(target[keys[-1]])}))
    reference.update(status="manual_override", overridden_at=datetime.now(timezone.utc).isoformat())
    case["sources"][path] = reference
    target[keys[-1]] = value
    return True


def evaluate(case):
    frozen = deepcopy(case)
    result = calculate(frozen)
    result["recommendation"] = recommend(result)
    if risk := risk_input(frozen):
        result["risk_assessment"] = assess(frozen, result, risk)
    result.update(case_id=frozen["case_id"], input_sha256=digest(frozen),
                  calculated_at=datetime.now(timezone.utc).isoformat(), case=frozen)
    return result


def select_terms(case, side, code):
    """Only an explicit selection of a new option upgrades a legacy catalog."""
    if code not in TERMS or side not in ("load", "discharge"):
        raise ValueError("INVALID_PORT_TERMS")
    if code not in case["terms_snapshot"]:
        old_version = case["terms_version"]
        case["terms_version"] = TERMS_VERSION
        case["terms_snapshot"] = serializable(deepcopy(TERMS))
        case["sources"]["terms_version"] = {
            "original": old_version, "status": "catalog_upgrade_on_user_selection",
            "source": TERMS[code]["source"]}
    return override(case, "ports." + side + ".terms", code)


def export_case(case):
    return json.dumps({"format": SCHEMA, "sha256": digest(case), "case": serializable(case)},
                      ensure_ascii=False, allow_nan=False, indent=2).encode("utf-8")


def import_case(raw):
    if len(raw) > 10_000_000:
        raise ValueError("CASE_PACKAGE_TOO_LARGE")
    data = json.loads(raw, object_pairs_hook=unique_object,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError("INVALID_JSON_NUMBER")))
    if not isinstance(data, dict) or data.get("format") != SCHEMA or not isinstance(data.get("case"), dict):
        raise ValueError("Paket lama tidak didukung. Buat kasus Freight Desk baru; data lama tidak diubah otomatis.")
    case = data["case"]
    if digest(case) != data.get("sha256"):
        raise ValueError("CASE_PACKAGE_HASH_MISMATCH")
    for field in ("sources", "market_snapshot", "report_snapshot", "profile_source"):
        if not isinstance(case.get(field), dict):
            raise ValueError("INVALID_CASE_METADATA:" + field)
    if not all(isinstance(v, dict) for v in case["sources"].values()):
        raise ValueError("INVALID_CASE_SOURCES")
    required = {"market_snapshot": ("tc_rates", "bunkers", "fetched_at"),
                "report_snapshot": ("records", "errors"),
                "profile_source": ("source_url", "document_version")}
    for field, keys in required.items():
        if not all(key in case[field] for key in keys):
            raise ValueError("INCOMPLETE_CASE_METADATA:" + field)
    calculate(case)
    risk_input(case)
    if case.get("formula_version") == "FD.1":
        case = deepcopy(case)
        case["formula_version"] = "FD.2"
        for side in ("load", "discharge"):
            case["ports"][side]["time_margin_percent"] = "0"
            case["sources"]["ports." + side + ".time_margin_percent"] = {
                "original": "0", "status": "migration_default",
                "source": "Paket FD.1: margin waktu tidak diterapkan"}
        case["sources"]["formula_version"] = {"original": "FD.1", "status": "migrated",
            "source": "Paket diverifikasi sebelum migrasi; margin 0% mempertahankan hasil"}
        calculate(case)
    return case


def matrix(base, origins, destinations, family, root, quantity_basis="nominal", port_overrides=None):
    if len(origins) * len(destinations) > 25:
        raise ValueError("MATRIX_MAX_25_CELLS")
    reference = calculate(base)["classes"][family][quantity_basis]
    base_rate = reference.get("freight_usd_mt")
    cells = []
    for destination in destinations:
        for origin in origins:
            derived = deepcopy(base)
            derived.pop("risk_assessment", None)
            inherited = []
            for side, chosen in (("load", origin), ("discharge", destination)):
                if (derived["ports"][side]["name"], derived["ports"][side]["country"]) != tuple(chosen):
                    derived["ports"][side].update(name=chosen[0], country=chosen[1], draft_limit_m=None)
                    inherited.append(side)
                    supplied = (port_overrides or {}).get((side, *chosen), {})
                    for field, value in supplied.items():
                        if field not in ("rate_mt_day", "port_da_usd", "draft_limit_m", "terms", "waiting_days", "allowance_days", "time_basis", "calendar", "time_margin_percent"):
                            raise ValueError("INVALID_MATRIX_PORT_OVERRIDE")
                        if field == "terms":
                            select_terms(derived, side, value)
                        else:
                            override(derived, "ports." + side + "." + field, deepcopy(value))
            # The exact base uses the same recorded distance, including manual overrides.
            if inherited:
                update_route(derived, root)
                reselect_saved_kobc(derived)
            try:
                result = evaluate(derived)
                scenario = result["classes"][family][quantity_basis]
                rate = scenario.get("freight_usd_mt")
                delta = freight_delta(rate, base_rate) if rate is not None and base_rate is not None else None
                cells.append({"origin": origin, "destination": destination, "rate": rate, "delta": delta,
                              "scenario": scenario, "result": result, "inherited_ports": inherited})
            except (ValueError, KeyError) as error:
                cells.append({"origin": origin, "destination": destination, "rate": None, "delta": None,
                              "error": str(error), "inherited_ports": inherited})
    return cells
