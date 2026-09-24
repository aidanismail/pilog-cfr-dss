# Product Charter - PILOG CFR DSS

## Product identity

PILOG CFR DSS is a prescriptive decision support system for evaluating a shipment as FOB, CFR with PILOG-owned/operated tonnage, CFR with chartered tonnage, or HOLD/NO_BID. It is currently a simulation-only product: all recommendations require human commercial approval and no system action may execute a quote, booking, fixture, hedge, or external write-back.

## Product problem

PILOG needs a repeatable way to decide whether accepting freight scope under CFR creates acceptable value after considering physical constraints, voyage economics, availability, risk, and authority. A higher CFR selling price alone is not a recommendation.

```text
case data
-> validated snapshot
-> deterministic calculation
-> eligible scenarios
-> rules and evidence
-> advisory recommendation
-> human review and learning
```

## Users

| Role | Need | System output | Human authority |
|---|---|---|---|
| Commercial/Business Development | Choose offer structure | FOB/CFR comparison and reasons | Validate buyer/contract and approve commercial action |
| Operations/Chartering | Validate operational choice | Capacity, timing, and cost evidence | Confirm availability and operational feasibility |
| Finance/Risk/Legal | Review exposure and controls | Margin, assumptions, status, reason codes | Approve policy, cost, risk, and contract matters |
| Management | Make authorised decision | Concise decision brief/audit trace | Approve, reject, or override |
| IT | Build safe, reproducible workflow | Deterministic pipeline and tests | Must not invent policy or approve action |

## Product principles

1. Prescriptive, not merely descriptive: propose an action with evidence.
2. Explainability first: facts, assumptions, formula trace, constraints, reasons, and authority status must be separate.
3. Human-in-the-loop: `CFR_RECOMMENDED` is not `CFR_APPROVED`.
4. Safe failure: missing, stale, non-comparable, or unvalidated input returns HOLD/BLOCK/CONDITIONAL, not false certainty.
5. Deterministic math: standard Python functions using `Decimal` are the sole authoritative calculator.
6. LLM boundary: LLMs may map variables, write/review code, and explain executed results; they must not invent inputs, calculate authoritative business values, or override Python results.
7. Mentor feedback is authoritative. GPT/Gemini notes are hypotheses until confirmed.

## Decision scope

### In scope for current simulation

- local CSV/manual case inputs;
- controlled manual Index and Alpha;
- deterministic voyage economics after data definitions are approved;
- Supramax and Handysize scenario families only;
- Gate 1 eligibility, Gate 2 choice, reason codes, decision brief, human handover;
- review/feedback loop across iterations.

### Out of scope

- auto-quotation, chartering, fixture, booking, hedge, approval, or write-back;
- live Fleetra, SAP, Procure-X, or market integration;
- ML pricing/prediction;
- CII, terminal/draft, and API-based checks without an approved data contract;
- production claims from the experimental Bontang -> ECI case.

## Core lifecycle

```text
DRAFT
-> DATA_CHECK
-> HOLD_DATA_ISSUE | READY_FOR_SCENARIOS
-> SCENARIOS_CALCULATED
-> GATE_1_EVALUATED
-> GATE_2_EVALUATED
-> RECOMMENDATION_READY
-> PENDING_HUMAN_REVIEW
-> APPROVED | OVERRIDDEN | REJECTED | NO_BID | EXPIRED
```

Only humans may transition a case to `APPROVED` or `OVERRIDDEN`.

## Decision architecture

```text
Data layer
  raw case, master vessel data, market inputs, policy inputs
->
Pre-process layer
  parse, normalize, validate unit/currency/source/freshness, snapshot
->
Process layer
  constraints, deterministic economics, scenario construction, Gate 1, Gate 2
->
Output layer
  recommendation, calculation trace, reasons, assumptions, approval handover
```

## Gate 1 - eligibility

Question: is the shipment sufficiently defined and permitted to enter CFR analysis?

Minimum evidence:

- cargo, quantity, origin, destination, and laycan;
- commercial/contractual CFR scope and PILOG authority;
- critical quality status is not BLOCK;
- enough decision time;
- controlled Index and Alpha inputs for the simulation.

Output: `CFR_ELIGIBLE`, `HOLD_DATA_ISSUE`, or `FOB_RECOMMENDED`.

## Gate 2 - scenario choice

Question: for each scenario, is it feasible, comparable, economically acceptable, within policy, and ready for human review?

Expected evidence:

- Supramax/Handysize vessel class;
- capacity/timing evidence where available;
- deterministic voyage cost and freight economics;
- comparable route, quantity, date, unit, currency, and cost boundary;
- approved margin/TCE/contribution rule;
- risk, clause, cash, and approval state;
- reason codes for every failed/unknown condition.

Output: `CFR_RECOMMENDED`, `CFR_CONDITIONAL`, `FOB_RECOMMENDED`, `HOLD_DATA_ISSUE`, or `NO_BID_RECOMMENDED`.

## Calculation contract

```text
FOB = Index + Alpha
CFR = FOB + Freight Selling Rate + Adjustment
Freight Contribution = Freight Selling Rate - Relevant Freight Cost
```

The above is a starting price abstraction, not complete transaction profit. Complete voyage economics require a mentor-approved cost boundary.

Required deterministic modules:

| Module | Purpose |
|---|---|
| Capacity | Determine cargo/vessel capacity status |
| Voyage days | Calculate laden, ballast, port, and total days |
| Fuel | Calculate approved fuel use and cost |
| Cost | Combine cost components without double-counting |
| Revenue | Calculate freight revenue/commission treatment |
| Economics | Calculate contribution and TCE only after definitions are approved |
| Scenarios | Build FOB, owned, chartered, and no-bid alternatives |
| Gates | Convert deterministic evidence to statuses/reason codes |
| Recommendation | Select among eligible scenarios using an approved objective |

## Data ownership and mandatory lineage

| Category | Examples | Owner/source |
|---|---|---|
| Master data | vessel class, DWT, equipment | approved Fleetra/master data |
| Case data | cargo, quantity, route, laycan, Incoterm | Commercial/Operations/manual import |
| Market data | Index, bunker, charter reference, FX | approved controlled source |
| Cost data | port cost, hire, running cost, commission | Finance/Chartering/approved source |
| Policy data | margin floor, authority, risk rules | approved management policy |
| Calculation output | days, cost, contribution, TCE | deterministic Python |
| Human decision | approval, override, comment | authorised user |

Every decision-critical input must carry: `case_id`, `scenario_id` if applicable, raw/normalized value, unit, currency, source, as-of/valid-until time, snapshot version, formula version, rule version, and approval state.

## Iteration 2 product requirements

1. Classify all 62 variables by calculation role or explicit unused reason.
2. Confirm what `Freight rate (USD/MT)` means before treating it as a selling rate, benchmark, or cost input.
3. Derive Freight Cost and Freight Selling Rate only where their business definitions are approved.
4. Keep Index and Alpha as controlled manual inputs.
5. Split calculations into pure, tested Python modules.
6. Make Gate 1 consume critical quality status.
7. Replace hardcoded feasibility/comparability with derived evidence where available; otherwise HOLD/CONDITIONAL.
8. Generate a prescriptive recommendation plus calculation trace and unresolved assumptions.

## Product output contract

Every decision brief must separate:

```text
Facts          - received data and lineage
Assumptions    - controlled/manual inputs and unresolved gaps
Calculations   - deterministic formula trace
Constraints    - pass/fail/unknown evidence
Scenarios      - FOB/owned/chartered/no-bid comparison
Recommendation - proposed action and reason codes
Authority      - human approval or override status
```

## MVP readiness

The product may move from simulation toward MVP only after formulas/cost boundary and Gate rules are mentor-approved, critical inputs have traceable source/unit/freshness metadata, multiple representative/edge cases are reproducible, and human approval/override is designed. A single successful simulation is not MVP readiness.

## Agent pre-change checklist

Before changing the product, an agent must answer:

1. Which user decision improves?
2. Is this simulation, MVP, or later production scope?
3. Which Python module owns the calculation?
4. What source, unit, timestamp, and owner are required?
5. What happens when input is missing/stale/not comparable?
6. Has the mentor approved the business definition/threshold?
7. Which test proves the expected behaviour?
8. Which iteration review/state item will record the result?

If an answer is unknown, create a blocker/task rather than inventing a policy.

