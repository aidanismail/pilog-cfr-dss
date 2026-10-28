"""Local editable cases. No Streamlit imports, financial formulas or awards."""
import csv
import hashlib
import io
import json
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4
from zipfile import ZipFile, ZIP_DEFLATED
from decimal import localcontext

from pilog_cfr_dss.models.iteration_04 import UNITS
from pilog_cfr_dss.orchestration.iteration_04 import evaluate, prepare_voyage, persist_run, fixed_freight_record
from pilog_cfr_dss.validation.iteration_04 import unique_object
from pilog_cfr_dss.calculations.tender_04 import index_prices, minimum_alpha
from pilog_cfr_dss.orchestration.iteration_04 import serial
from pilog_cfr_dss.validation.iteration_04 import number
from pilog_cfr_dss.validation.cost_forecast import COST_KEYS, FORECAST_VERSION, REVIEW_VERSION, forecast_values, quote_basis_hash


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _manual(record: dict) -> None:
    record.setdefault("prior_source", {key: record.get(key) for key in
                      ("source_status", "source_reference", "sha256", "observation_date", "source_observed_on", "source_observed_at", "source_snapshot_id")})
    record.update(source_status="simulation_only_user_input", source_reference="Input manual pada draft UI lokal")
    from pilog_cfr_dss.orchestration.price_records import utc_now
    record["edited_at"] = utc_now()
    for key in ("sha256", "observation_date", "source_observed_on", "source_observed_at", "source_fetched_at", "source_snapshot_id"):
        record.pop(key, None)


@dataclass
class InteractiveCase:
    context: dict
    rows: list[dict[str, str]]
    draft_id: str = field(default_factory=lambda: "ui_" + uuid4().hex)
    revision: int = 0
    preparation: dict | None = None
    result: dict | None = None
    run_dir: Path | None = None
    _saved: tuple[str, Path] | None = None

    @classmethod
    def read(cls, path: Path) -> "InteractiveCase":
        context = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object)
        name = context.get("voyage_dataset") if isinstance(context, dict) else None
        if not isinstance(name, str) or Path(name).name != name or not name.endswith(".csv"):
            raise ValueError("INVALID_DATASET_PATH")
        dataset = path.parent / name
        if dataset.resolve().parent != path.parent.resolve():
            raise ValueError("INVALID_DATASET_PATH")
        with dataset.open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream))
        return cls(context, rows)

    @classmethod
    def reopen(cls, path: Path, drafts_root: Path) -> "InteractiveCase":
        path, drafts_root = path.resolve(), drafts_root.resolve()
        if not path.is_relative_to(drafts_root) or path.name != "case_fixture.json":
            raise ValueError("DRAFT_OUTSIDE_LOCAL_WORKSPACE")
        return cls.read(path)

    @property
    def fixed(self) -> bool:
        return self.context.get("freight_tender") is not None

    @property
    def state(self) -> str:
        if self.result is not None:
            return "DSS_EVALUATED"
        if self.fixed:
            return "BIDS_READY" if self.context.get("bids") else "FREIGHT_FIXED"
        return "VOYAGE_CALCULATED" if self.preparation is not None else "DRAFT"

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(_json({"context": self.context, "rows": self.rows}).encode("utf-8")).hexdigest()

    def _invalidate(self, *, voyage: bool = False) -> None:
        self.revision += 1
        self.result, self.run_dir, self._saved = None, None, None
        if voyage:
            self.preparation = None

    def values(self) -> dict[str, str]:
        return {row["key"]: row["value"] for row in self.rows}

    def current_values(self) -> dict[str, str]:
        return serial(forecast_values(self.context, self.rows, self.values()))

    def reforecast_costs(self, values: dict[str, str], reason: str) -> "InteractiveCase":
        """New estimate, same commercial quote/bids; never mutate a prior estimate/run."""
        if not self.fixed:
            raise ValueError("FREIGHT_NOT_FIXED")
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("COST_FORECAST_REASON_REQUIRED")
        if not isinstance(values, dict) or set(values) - set(COST_KEYS):
            raise ValueError("UNSUPPORTED_COST_FORECAST_FIELD")
        from pilog_cfr_dss.orchestration.price_records import utc_now
        overrides = deepcopy(self.context.get("cost_forecast", {}).get("overrides", {}))
        original = self.values()
        for key, raw in values.items():
            value = number(raw, key)
            if value == number(original[key], key):
                overrides.pop(key, None)
            else:
                overrides[key] = {"value": str(value), "unit": UNITS[key],
                    "source_status": "simulation_only_user_cost_reforecast", "source_reference": reason.strip()}
        context = deepcopy(self.context)
        previous = context.get("cost_forecast", {})
        context["commercial_review_version"] = REVIEW_VERSION
        context["cost_forecast"] = {"version": FORECAST_VERSION, "forecast_id": "cost_" + uuid4().hex,
            "parent_forecast_id": previous.get("forecast_id"), "recorded_at": utc_now(),
            "reason": reason.strip(), "basis_price_id": context["freight_tender"].get("price_id"),
            "basis_hash": quote_basis_hash(self.rows, context["freight_tender"]), "overrides": overrides}
        forecast_values(context, self.rows, self.values())
        return InteractiveCase(context, deepcopy(self.rows))

    def market_summary(self) -> dict:
        with localcontext() as precision:
            precision.prec = 40
            prices = index_prices(self.context["market_index"])
            prices["minimum_alpha_usd_mt"] = minimum_alpha(
                prices["index_usd_mt"], number(self.context["oe_hps"]["value"], "OE/HPS"))
            return serial(prices)

    def tender_preview(self) -> list[dict]:
        """Read-only prices/status through the same calculation and tender rules as evaluation."""
        from pilog_cfr_dss.calculations.tender_04 import bid_prices
        from pilog_cfr_dss.decisions.iteration_04 import evaluate_tender
        if not self.fixed:
            raise ValueError("FREIGHT_NOT_FIXED")
        with localcontext() as precision:
            precision.prec = 40
            index = index_prices(self.context["market_index"])["index_usd_mt"]
            prices = bid_prices(index, number(self.context["oe_hps"]["value"], "OE/HPS"),
                                number(self.context["freight_tender"]["value"], "freight"), self.context.get("bids", []))
            return serial(evaluate_tender(prices, self.context)["bids"])

    def apply_inputs(self, values: dict[str, str], *, target_tce: str,
                     observations: dict[str, dict[str, str]], oe_hps: str) -> None:
        if self.fixed:
            raise ValueError("BASIS_FIXED_CREATE_REVISION")
        if set(values) - set(UNITS):
            raise ValueError("UNKNOWN_VOYAGE_FIELD")
        from pilog_cfr_dss.validation.case_basis import BASIS_VERSION, COMMISSION_KEYS
        if self.context.get("case_basis_version") == BASIS_VERSION:
            if any(key in values and number(values[key], key) != 0 for key in COMMISSION_KEYS):
                raise ValueError("ACTIVE_CASE_COMMISSION_MUST_BE_ZERO")
            if "distance_nm" in values and number(values["distance_nm"], "distance_nm") != number(self.context["distance_reference"]["value"], "distance_nm"):
                raise ValueError("OD_DISTANCE_SOURCE_BINDING_MISMATCH")
        changed = False
        for row in self.rows:
            key = row["key"]
            if key in values and row["value"] != str(values[key]).strip():
                row["value"] = str(values[key]).strip()
                row["note"] = (row.get("note", "") + " | Diubah manual di UI; sumber awal: " + row.get("source_reference", "")).strip(" |")
                row["source_status"] = "simulation_only_user_input"
                row["source_reference"] = "Input manual pada draft UI lokal"
                changed = True
        target = self.context["pricing"]["target_tce"]
        if target["value"] != str(target_tce).strip():
            _manual(target); target["value"] = str(target_tce).strip(); changed = True
        for publisher, edits in observations.items():
            if publisher not in {"argus", "fertecon"} or set(edits) - {"low", "high"}:
                raise ValueError("UNKNOWN_INDEX_FIELD")
            observation = self.context["market_index"][publisher]
            for key, value in edits.items():
                if observation[key] != str(value).strip():
                    _manual(observation); observation[key] = str(value).strip(); changed = True
        floor = self.context["oe_hps"]
        if floor["value"] != str(oe_hps).strip():
            _manual(floor); floor["value"] = str(oe_hps).strip(); changed = True
        if changed:
            self._invalidate(voyage=True)

    def revise(self) -> "InteractiveCase":
        """New tender basis, deliberately not carrying bids into a new price."""
        context = deepcopy(self.context)
        rows = deepcopy(self.rows)
        if context.get("cost_forecast"):
            current = self.current_values()
            forecast = context.pop("cost_forecast")
            for row in rows:
                if row["key"] in forecast["overrides"]:
                    row.update(value=current[row["key"]], source_status="simulation_only_user_input",
                        source_reference="Cost forecast " + forecast["forecast_id"], note=forecast["reason"])
        context.pop("freight_tender", None)
        context.pop("pi_selected_bid_id", None)
        context["bids"] = []
        context["case_id"] = "UI-CFR-" + uuid4().hex[:8].upper()
        if context.get("auction_clock"):
            from pilog_cfr_dss.orchestration.price_records import utc_now
            from pilog_cfr_dss.models.tender_clock import round_window
            context["auction_clock"]["starts_at"] = utc_now()
            context["evaluation_cutoff"] = round_window(context["auction_clock"], 3)[1].isoformat()
        return InteractiveCase(context, rows)

    def save(self, drafts_root: Path) -> Path:
        signature = self.fingerprint
        if self._saved is not None and self._saved[0] == signature and self._saved[1].exists():
            return self._saved[1]
        root = drafts_root.resolve()
        folder = root / self.draft_id / f"revision_{self.revision:04d}_{uuid4().hex[:8]}"
        if not folder.resolve().is_relative_to(root):
            raise ValueError("DRAFT_OUTSIDE_LOCAL_WORKSPACE")
        name = self.context.get("voyage_dataset")
        if not isinstance(name, str) or Path(name).name != name or not name.endswith(".csv"):
            raise ValueError("INVALID_DATASET_PATH")
        folder.mkdir(parents=True, exist_ok=False)
        with (folder / name).open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(self.rows[0]))
            writer.writeheader(); writer.writerows(self.rows)
        path = folder / "case_fixture.json"
        path.write_text(_json(self.context), encoding="utf-8")
        self._saved = (signature, path)
        return path

    def prepare(self, drafts_root: Path) -> dict:
        self.preparation = None
        self.result, self.run_dir = None, None
        result = prepare_voyage(self.save(drafts_root))
        self.preparation = result
        return result

    def fix_freight(self, drafts_root: Path, rate: str | None = None, reason: str = "") -> None:
        if self.fixed:
            return
        if self.preparation is None:
            raise ValueError("CALCULATE_VOYAGE_FIRST")
        record = deepcopy(fixed_freight_record(self.preparation))
        if rate is not None:
            value = number(rate, "freight offer")
            if value < 0:
                raise ValueError("NEGATIVE_FREIGHT_OFFER")
            if value != number(record["value"], "freight indication"):
                if not isinstance(reason, str) or not reason.strip():
                    raise ValueError("MANUAL_FREIGHT_REASON_REQUIRED")
                record.update(value=str(value), source_status="simulation_only_manual_fixed_tender_rate",
                    source_reference="Commercial offer input: " + reason.strip(), manual_reason=reason.strip())
                record["indicated_freight_usd_mt"] = self.preparation["pricing"]["computed_freight_usd_mt"]
                record["buyer_acceptance"] = "NOT_RECORDED"
                self.context["commercial_review_version"] = REVIEW_VERSION
        self.context["freight_tender"] = record
        self._invalidate()
        self.save(drafts_root)
        self.prepare(drafts_root)

    def apply_tender(self, bids: list[dict], cutoff: str, selection: str | None = None, auction_start: str | None = None) -> None:
        if not self.fixed:
            raise ValueError("FREIGHT_NOT_FIXED")
        normalized = []
        for row in bids:
            if all(value is None or str(value).strip() == "" for value in row.values()):
                continue
            bid = {key: _text(row.get(key, "")) for key in
                   ("bid_id", "buyer_id", "alpha_usd_mt", "status")}
            try:
                for key in ("round", "sequence"):
                    value = str(row.get(key, "")).strip()
                    if not value.isdigit():
                        raise ValueError
                    bid[key] = int(value)
            except ValueError:
                raise ValueError("Putaran dan urutan harus bilangan bulat positif.") from None
            for key in ("submitted_at", "valid_until"):
                value = _text(row.get(key, ""))
                if value:
                    bid[key] = value
            bid["source_status"] = "simulation_only_user_input"
            normalized.append(bid)
        clock_changed = auction_start is not None and auction_start != self.context.get("auction_clock", {}).get("starts_at")
        if clock_changed:
            from pilog_cfr_dss.validation.iteration_04 import timestamp
            timestamp(auction_start)
            self.context["auction_clock"] = {"mode": "fixed_window", "round_duration_seconds": 180, "starts_at": auction_start}
        if not clock_changed and (normalized, cutoff, selection) == (self.context.get("bids"), self.context.get("evaluation_cutoff"), self.context.get("pi_selected_bid_id")):
            return
        self.context.update(bids=normalized, evaluation_cutoff=cutoff)
        if selection:
            self.context["pi_selected_bid_id"] = selection
        else:
            self.context.pop("pi_selected_bid_id", None)
        self._invalidate()

    def apply_scenarios(self, rows: list[dict]) -> None:
        scenarios = []
        for row in rows:
            if all(value is None or str(value).strip() == "" for value in row.values()):
                continue
            scenarios.append({**{key: _text(row.get(key, "")) for key in
                              ("scenario_id", "label", "fuel_price_increase_fraction", "extra_port_days")},
                              "source_status": "simulation_only_user_input"})
        if scenarios != self.context.get("scenarios"):
            self.context["scenarios"] = scenarios
            self._invalidate()

    def evaluate(self, drafts_root: Path, runs_root: Path) -> dict:
        if not self.fixed:
            raise ValueError("FREIGHT_NOT_FIXED")
        if self.result is not None and self.run_dir is not None:
            return self.result
        result = evaluate(self.save(drafts_root))
        folder = persist_run(result, runs_root)
        self.result = json.loads((folder / "result.json").read_text(encoding="utf-8"))
        self.run_dir = folder
        return self.result

    def bundle(self) -> bytes:
        if self.run_dir is None or self.result is None:
            raise ValueError("NO_CURRENT_RESULT")
        buffer = io.BytesIO()
        with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
            for file in self.run_dir.rglob("*"):
                if file.is_file():
                    archive.write(file, file.relative_to(self.run_dir).as_posix())
        return buffer.getvalue()
