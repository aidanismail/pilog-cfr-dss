---
name: pilog-calculation-engine
description: Implement and test deterministic, modular Python calculation functions for the PILOG CFR DSS while preserving units, data lineage, safe failure, and reproducible output traces.
---

# PILOG Calculation Engine

Use this skill when creating, moving, refactoring, or testing code under `src/pilog_cfr_dss`.

## Architecture boundary

```text
models -> validation/calculations -> scenarios -> decisions -> reporting -> orchestration
```

Only `calculations` may own business arithmetic. `reporting`, Excel generation, prompts, JSON policy files, UI, and CLI runners must not contain hidden formula logic.

## Engineering rules

- Use pure functions with explicit typed inputs/outputs.
- Use `Decimal` for money, rates, quantities, and intermediate financial values.
- Require explicit unit conversion. Never mix USD, USD/MT, USD/day, MT, day, knot, or lump sum implicitly.
- Return structured errors/status for missing, invalid, stale, or incompatible inputs; do not silently coerce to zero.
- Keep I/O at orchestration boundaries. Calculation functions should not read files, call APIs, print, or mutate global state.
- Store formula version, input snapshot ID, assumption IDs, and reason codes in output objects.
- Preserve existing Iteration 1 scripts until tested modules replace their responsibilities.

## Test minimum

For every calculation module, add:

```text
happy-path numeric test
boundary test
missing-input test
unit/currency mismatch test when relevant
regression/golden-case test after mentor validates an example
```

The golden expected values must come from approved evidence or executed Python—not LLM reasoning.

