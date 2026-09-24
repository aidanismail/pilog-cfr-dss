# Simulation Iteration 1 Review

## Purpose

Iteration 1 proved that a simple advisory-only CFR DSS workflow can run from dataset inspection to a decision brief. It did **not** prove that a real PILOG shipment should be sold CFR or that the freight economics are production-ready.

## What was demonstrated

```text
CSV dataset
-> inspect / ingest / quality / normalize
-> generic FOB-CFR calculation
-> simple scenarios
-> Gate 1 and Gate 2 prototype
-> explainable decision brief
-> human-review boundary
```

The initial alternatives were FOB baseline, CFR with a PILOG vessel, CFR with voyage charter, and defer/no-bid.


## Aidan's Feedback - Optional suggestions to make it easier for me to understand
- Group all variables by the calculation they support.
- after grouping, make it into an explainable excel file for me to learn (not helpful for the system itself, but its for me as an intern to support my knowledge)
- program shouldnt be hardocded chekcing ECI <-> India, i need to be able to conduct experiments with differernt routes also, and dont mention aqaba again, the different routes will be set manually in the excel dataset file

## Actual mentor feedback - authoritative

Source: `docs/it_1/simul_it_1.md`.

1. Derive Freight Cost and Freight Selling Rate from the existing dataset where possible, dont hardcode freight cost and selling rate from the command.
2. Limit vessel options to Supramax and Handysize because PILOG targets only supports both of those vessels.
3. Keep Index and Alpha as manual controlled inputs for now.
4. Separate calculation modules.
5. Make the system prescriptive, not descriptive.

## GPT takeaway - accepted design guardrails

Source: `docs/it_1/gpt_takeaway.md`.

- The product is a business DSS, not a maximal maritime optimisation engine.
- Higher CFR revenue is not sufficient; compare economics, operational feasibility, and risk.
- Prioritise explainability, maintainability, and human-in-the-loop review.
- Keep advanced risk, hedging, ML, and historical prediction outside the first MVP unless there is a validated business need.

## Gemini takeaway - candidate backlog, not confirmed requirements

Source: `docs/it_1/gemini_takeaway.md`.

Potential future ideas include physical constraints, speed optimisation, fuel routing, CII, TCE, and benchmark adjustment. These are useful hypotheses, but several required inputs are absent from the current dataset:

- port maximum draft;
- cargo stowage factor;
- terminal geared/un-geared status;
- external fuel price feed;
- vessel annual CII baseline/rating;
- approved CII methodology and business policy.

Therefore these ideas are not Iteration 2 requirements unless mentor approves the business need and data contract.

## Critical findings from the I1 pipeline

| Finding | Why it matters | Iteration 2 action |
|---|---|---|
| Freight cost and selling rate were hardcoded scenario assumptions. | The result cannot represent actual voyage economics. | Derive them with validated deterministic modules. |
| Feasibility and comparability were hardcoded flags. | Gate outcomes are not evidence-backed. | Derive checks where data exists; HOLD where evidence is missing. |
| Quality report can be `BLOCK` while Gate 1 reports `CFR_ELIGIBLE`. | Critical data quality does not control the decision path. | Make Gate 1 consume quality status. |
| The experimental route was changed from Aqaba to Bontang -> ECI. | Other voyage fields may not match the experimental route. | Keep the caveat visible and validate with mentor. |
| The decision brief mixed operating mode and quality status. | Readers can misunderstand `advisory-only` as data quality. | Separate operating mode, quality state, and recommendation state. |
| Many of the 62 variables were stored but not used. | The dataset has unrealised calculation potential. | Classify every variable before building modules. |

## Iteration 1 conclusion

Status: `reviewed; needs Iteration 2`.

The right next move is not a UI or integration. It is a deterministic, modular voyage-economics and prescriptive-decision foundation that the mentor can inspect and challenge.

