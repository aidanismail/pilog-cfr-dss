---
name: pilog-route-data-contract
description: Build and validate route-agnostic PILOG shipment input contracts, variable maps, units, lineage, and educational Excel artefacts without embedding route assumptions in code.
---

# PILOG Route and Data Contract

Use this skill when working with CSV/Excel inputs, the 62-variable register, port/route fields, units, variable grouping, data lineage, or learning workbooks.

## Core invariant

Origin and destination are case inputs. Never write business logic that checks a specific port, country, route, or customer name unless an approved policy explicitly requires it.

```text
selected input dataset
-> loading_port + discharging_port
-> route-specific evidence
-> calculation or HOLD_DATA_ISSUE
```

Do not reuse distance, tariff, port time, terminal condition, or restriction from a different route when a selected route lacks data.

## Variable-map contract

For every source variable, capture:

```text
raw label
canonical key
row/source
data type
unit and currency
route-dependent flag
scenario-dependent flag
role: input / derived / reference / policy / output
module or validation rule
current use
intended use
source/as-of status
missing dependency or assumption
```

Every variable must have an explicit role or `unused_for_now` reason. Do not silently discard fields.

## Data-quality behaviour

- Missing decision-critical data: `HOLD_DATA_ISSUE` or `BLOCK`.
- Unknown unit/currency/basis: do not compare or calculate across it.
- Stale time-sensitive data: show freshness state and apply approved policy.
- Manual Index/Alpha are allowed only as controlled inputs with source, owner, as-of date, and simulation status.

## Educational Excel

An Excel variable map may be generated for intern/mentor learning. It is not a system-of-record or formula engine. Python code and tests remain authoritative for calculations.

