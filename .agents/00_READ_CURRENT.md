# Current Agentic Control State

## Status as of 2026-09-24

The **revised Iteration 2 simulation is implemented and technically verified**: 26 automated tests pass and the pre-offer CSV case reaches both Gates in `outputs/runs/i2_20260923T091307166739Z_f5c4e74a/`. It uses seller-capped DWCC 45,000 MT for all economics, PI Group as commodity seller, PILOG as freight provider, CSV as simulation numerical ground truth, and versioned DWT class ranges. The active revision task board is `tasks/ITERATION_02_PROPOSED.md`; the plan is `PLANS_ITERATION_02.md`. Repo cleanup on 24 September retained this one complete run, removed nine earlier generated runs and obsolete active inputs/outputs, and updated ignore rules/README. No Git stage, commit, or push was performed. **Mentor acceptance remains pending**; this is simulation-only and must not be treated as MVP or quotation authority. Confirm company permission and repo visibility before publishing the Aqaba-derived dataset or its run snapshot.

## Current authoritative reading order

1. `AGENTS.md`
2. `PRODUCTS.MD`
3. `PRODUCTS_TIMELINE_PROPOSAL.md` - approved timeline clarification; use it to interpret product maturity.
4. `ITERATION_STATE.json`
5. `reviews/ITERATION_01.md`
6. `tasks/ITERATION_02_PROPOSED.md` - approved Iteration 2 task board.
7. `PLANS_ITERATION_02.md` - executed technical plan.
8. `reviews/ITERATION_02.md` - current review pack; not mentor-approved yet.
9. `contracts/ITERATION_02_ECONOMICS.md` - candidate economic definitions.
10. `ITERATION_02_RUNBOOK.md` - repeatable test/run procedure.
11. `ARCHITECTURE.md`
12. `DECISIONS.md`

`tasks/ITERATION_02.md` and the older sections of `PRODUCTS.MD` remain historical. Do not use them to override the approved documents above. Do not treat a synthetic test fixture or a conditional code path as mentor-approved economics.

## Work boundary

```text
Simulation -> Iteration 1..N -> Final Simulation Validation -> MVP consideration
```

MVP work is prohibited until the mentor accepts Final Simulation Validation.
