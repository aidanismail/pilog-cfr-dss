# Iteration 2 Task Board

## Iteration objective

Convert the simple CFR calculator into a deterministic, modular, evidence-backed prescriptive DSS prototype while remaining in simulation mode.

## Working rules

- Complete tasks in order unless a task explicitly permits parallel work.
- A task is not complete without tests and review evidence.
- A blocked task is a valid outcome; do not fabricate a value or policy to unblock it.
- Use `Decimal`, explicit units, and pure Python functions for every calculation.

## Task list

### I2-T01 - Variable calculation map

**Status:** ready

Classify all 62 dataset variables into:

```text
case/transaction
route and timing
vessel capacity
fuel and consumption
port operation
cost and commission
benchmark/reference
unsupported/future
```

For each variable, record:

```text
canonical key, raw label, unit, source row,
calculation module, role, required/optional,
current use, future use, data gap/assumption
```

**Acceptance criteria:** no variable is silently ignored; each has a documented role or explicit `unused_for_now` reason.

### I2-T02 - Data contract and price-object clarification

**Status:** blocked pending mentor/domain confirmation

Clarify:

1. Is `Freight rate (USD/MT)` the customer freight selling rate, charter market rate, benchmark, or another price object?
2. Which cost components belong in owned-vessel freight cost versus chartered-vessel freight cost?
3. Are `Other voyage costs total`, `Daily cost assumption`, `Hire rate`, and `Running costs` mutually exclusive or cumulative?
4. What is the accepted cost boundary for the prescriptive comparison?

**Acceptance criteria:** an approved written mapping exists. Until then, relevant economic output must be `HOLD_DEFINITION_REQUIRED`.

### I2-T03 - Deterministic calculation modules

**Status:** blocked by I2-T01 and partially by I2-T02

Build/test pure modules for the approved variables only:

```text
capacity
voyage_days
fuel_consumption_and_cost
port_days
commission
voyage_cost
freight_cost_per_mt
revenue_and_contribution
TCE (only if mentor approves the cost boundary)
```

**Acceptance criteria:** each module has a typed input/output contract, `Decimal` calculation, unit test, boundary test, and no hidden global/hardcoded business value.

### I2-T04 - Prescriptive scenarios and gates

**Status:** blocked by I2-T03

Create only these scenario families:

```text
FOB
CFR owned/operated Supramax
CFR owned/operated Handysize
CFR chartered Supramax
CFR chartered Handysize
HOLD or NO_BID
```

Requirements:

- Gate 1 consumes critical quality status.
- Gate 2 consumes calculated evidence instead of manual `feasible`/`comparable` flags where possible.
- Missing evidence produces HOLD/CONDITIONAL, never an approval.
- Recommendation must state the decision objective and reason codes.

**Acceptance criteria:** changing a validated input changes the deterministic output and reason codes through tests.

### I2-T05 - Review pack and iteration close

**Status:** blocked by I2-T04

Produce:

```text
input snapshot
calculation trace
scenario comparison
Gate evidence
prescriptive recommendation
assumptions and gaps
mentor questions
test evidence
```

Update `.agents/reviews/ITERATION_02.md`, `.agents/DECISIONS.md`, and `ITERATION_STATE.json` after mentor review.

**Acceptance criteria:** mentor can challenge every recommendation without opening calculation source code.

## Explicit non-tasks for I2

- Build a web UI.
- Connect live APIs.
- Implement CII without approved data/methodology.
- Build ML models.
- Automate quote/fixture/hedging/approval.

