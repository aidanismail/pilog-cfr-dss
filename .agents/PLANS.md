# Iteration Plan - PILOG CFR DSS

**Status 2026-09-24:** revisi teknis Iteration 2 selesai, 26 tes lulus, dan satu contoh run lengkap dipertahankan; **review/penerimaan mentor belum ada**. Rencana rinci ada di `PLANS_ITERATION_02.md`; hasil aktual dan pertanyaan keputusan ada di `reviews/ITERATION_02.md`. Struktur kode aktual mengikuti `src/pilog_cfr_dss/`; sketsa modul di bawah bersifat historis. Tidak ada persetujuan untuk MVP.

## Product objective

Build a transparent, prescriptive DSS. In the active revised Iteration 2 simulation, commercial alternatives are FOB and CFR; vessel-class choice is nested in CFR, owned-vessel economics only, while defer/no-bid are outcomes. Chartered tonnage and broader choice sets belong to later iterations only after mentor feedback. The system recommends an action and explains the evidence; humans retain commercial authority.

## Non-negotiable scope boundaries

- Current mode is simulation, not production.
- No external write-back or transaction execution.
- Index and Alpha are controlled manual inputs until a mentor-approved source/definition exists.
- All money/rate calculations run in deterministic Python functions, not in LLM reasoning.
- Mentor feedback is authoritative. AI suggestions are hypotheses until accepted.
- The pilot dataset is experimental Bontang -> ECI data with an Aqaba-derived route override.

## Iteration lifecycle

```text
PLAN -> TASK -> EXECUTE -> REVIEW -> UPDATE STATE -> NEXT ITERATION
```

Every iteration needs a clear objective, task list, data contract, acceptance criteria, test evidence, review record, and explicit next state.

## Iteration 1 - completed/reviewed

Goal: demonstrate a simple end-to-end CFR DSS simulation.

Delivered:

- inspect, ingest, quality, and normalize pipeline;
- generic `FOB = Index + Alpha` and `CFR = FOB + Freight + Adjustment`;
- simple freight margin;
- initial scenarios and Gate 1/Gate 2;
- decision brief; advisory-only boundary.

Review conclusion: good workflow proof, but not yet a credible voyage economics engine. See `reviews/ITERATION_01.md`.

## Iteration 2 - implemented, pending mentor review

Goal: replace the most important hardcoded economic assumptions with deterministic, modular voyage-economics calculations and produce an evidence-backed prescriptive recommendation.

In scope:

1. Classify the 61 active dataset variables by calculation role, owner, unit, and status; the obsolete 46,000 MT allocation row is excluded.
2. Create pure Python calculation modules with tests.
3. Limit vessel-class scenarios to Supramax and Handysize.
4. Derive voyage days, fuel usage/cost, commission, voyage cost, and relevant freight economics from approved available inputs.
5. Define precisely whether dataset `Freight rate (USD/MT)` is a selling rate, a market reference, or another object before using it.
6. Make Gate 1 consume critical data-quality status.
7. Replace descriptive outputs with a bounded prescriptive recommendation and reason codes.
8. Preserve explicit HOLD/BLOCK when a required variable, unit, or economic definition is missing; deferred source/as-of metadata is a simulation WARN, not a Gate.

Not in scope unless mentor explicitly confirms required data and business relevance:

- live APIs;
- CII compliance calculation;
- automated draft/terminal gear checks using unprovided port data;
- automatic pricing/quotation;
- ML, hedging, or optimisation beyond deterministic scenario selection.

## Target module boundaries for Iteration 2

```text
src/
  models.py                 # typed canonical input/output models
  constants.py              # explicit units and approved constants only
  validation/
    quality.py              # completeness, units, freshness, basis
    constraints.py          # only constraints backed by available data
  calculations/
    capacity.py             # cargo/vessel capacity checks
    voyage_days.py          # sea and port days
    fuel.py                 # consumption and fuel cost
    costs.py                # port, hire/running, commission, other cost
    economics.py            # freight cost, revenue, contribution, TCE if approved
  decisions/
    scenarios.py            # historical sketch; revised I2 uses FOB/CFR with vessel class inside CFR
    gates.py                # Gate 1/Gate 2 rules and reason codes
    recommendation.py       # deterministic prescriptive choice among eligible scenarios
```

The final layout may be adapted to the current repository structure, but business formula boundaries must remain separate.

## Decision order for Iteration 2

```text
1. Load CSV, catalog, manual context, and versioned vessel-class policy.
2. Validate required values, units, route, pricing inputs, and cost definitions; record deferred provenance as WARN.
3. Evaluate Gate 1 pre-offer eligibility; an uncontacted buyer is normal.
4. If Gate 1 permits, calculate deterministic voyage days, fuel, and PILOG freight economics.
5. Build FOB price baseline and CFR alternative; screen Handysize/Supramax inside CFR using gross DWT only.
6. Evaluate Gate 2 using available evidence and positive freight contribution as a review signal, not an approved margin floor.
7. Produce recommendation, reason codes, unresolved assumptions, and one auditable decision brief.
8. Require human review; do not execute a commercial action.
```

## Definition of done for Iteration 2

Iteration 2 is ready for review only when:

- every used variable has an explicit calculation role, unit, and source status;
- all new economics formulae are pure Python functions with tests;
- no calculation result is hand-authored by an LLM;
- Freight Rate is treated as PILOG's selling rate for this simulation; source/as-of is an explicit limitation;
- Gate 1 cannot return eligible when critical quality is blocked;
- commercial alternatives are FOB and CFR; vessel-class screening is nested within CFR;
- output gives a prescriptive CFR candidate, DEFER, or explicit HOLD with reasons; NO_BID is not asserted without FOB economics;
- the decision brief separates facts, assumptions, calculated outputs, and human approvals;
- an Iteration 2 review records mentor feedback and the next iteration plan.

## Transition to MVP

Do not transition simply because one case produces a recommendation. Move toward MVP only after multiple representative/edge cases are reproducible, formulas and rules are mentor-approved, evidence/source fields are present, and feedback cycles show stable logic.
