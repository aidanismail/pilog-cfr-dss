---
name: pilog-prescriptive-dss
description: Design and review PILOG CFR DSS scenarios, Gate 1/Gate 2 rules, recommendation statuses, reason codes, and human-in-the-loop controls for prescriptive—not merely descriptive—decision support.
---

# PILOG Prescriptive DSS

Use this skill when implementing scenarios, Gate 1, Gate 2, recommendation logic, decision briefs, overrides, or decision explanation.

## Product distinction

Descriptive output says:

```text
Here are cost, rate, and vessel data.
```

Prescriptive output says:

```text
Recommended action: <action>
Because: <deterministic evidence and reason codes>
Conditions: <remaining human approvals or unknowns>
```

The system recommends; authorised humans decide and execute.

## Gate 1 - case eligibility

Gate 1 asks whether a case may enter CFR analysis. It must consume critical quality status, not separate hardcoded booleans alone.

Typical evidence:

- cargo, quantity, route, laycan, and commercial scope;
- contract/buyer/PILOG freight authority;
- sufficient decision time;
- controlled pricing inputs;
- critical data quality is not blocked.

Outcomes:

```text
CFR_ELIGIBLE | HOLD_DATA_ISSUE | FOB_RECOMMENDED
```

## Gate 2 - scenario choice

Gate 2 evaluates alternatives from one validated case snapshot. Limit vessel classes to Supramax and Handysize unless mentor policy changes.

Evaluate, with evidence where data exists:

- physical/operational feasibility;
- route, quantity, unit, currency, date, and cost-boundary comparability;
- deterministic freight economics;
- approved objective/threshold;
- risk, clause, cash, competitiveness, and approval state.

Outcomes:

```text
CFR_RECOMMENDED
CFR_CONDITIONAL
FOB_RECOMMENDED
HOLD_DATA_ISSUE
NO_BID_RECOMMENDED
PENDING_HUMAN_REVIEW
```

Rank only eligible and comparable scenarios. If evidence is missing, report the exact condition; do not make a scenario pass by default.

## Output contract

Separate facts, assumptions, calculation trace, constraints, scenario result, recommendation, reason codes, and human authority status. `CFR_RECOMMENDED` is never equivalent to `CFR_APPROVED`.

