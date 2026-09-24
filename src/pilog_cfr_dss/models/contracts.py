from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


FORMULA_VERSION = "I2.R2.1"
RULE_VERSION = "I2.R2.1"


@dataclass(frozen=True)
class CaseSnapshot:
    case_id: str
    dataset_sha256: str
    manual_sha256: str
    origin: str
    destination: str
    values: dict[str, Decimal | str | bool | None]
    raw_rows: dict[str, dict[str, Any]]
    manual: dict[str, Any]

    def number(self, key: str) -> Decimal:
        value = self.values.get(key)
        if not isinstance(value, Decimal):
            raise ValueError(f"MISSING_NUMERIC_INPUT:{key}")
        return value


@dataclass(frozen=True)
class QualityResult:
    status: str
    checks: tuple[dict[str, Any], ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class CostLine:
    code: str
    amount_usd: Decimal
    mechanisms: frozenset[str]


@dataclass(frozen=True)
class ScenarioEvidence:
    scenario_id: str
    sales_term: str
    vessel_class: str | None
    vessel_mode: str | None
    feasible: bool | None
    comparable: bool | None
    contribution_usd: Decimal | None
    calculation_status: str
    reasons: tuple[str, ...] = field(default_factory=tuple)
