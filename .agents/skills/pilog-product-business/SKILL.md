---
name: pilog-product-business
description: Frame PILOG CFR DSS work as a business decision-support product, prioritise stakeholder value and explainability, and keep simulation iterations separate from MVP and production scope.
---

# PILOG Product and Business Thinking

Use this skill for product scope, user needs, prioritisation, stakeholder review, success criteria, decision-brief design, and MVP-readiness discussions.

## Product objective

Help PILOG decide whether freight scope under CFR creates acceptable value compared with FOB, owned/operated tonnage, chartered tonnage, or no-bid/hold. The product does not optimise for CFR percentage, revenue, or model sophistication alone.

## Stakeholder questions before building

For every proposed feature, answer:

1. Which decision and user does it improve?
2. What recurring error, delay, or information gap does it reduce?
3. What evidence must a reviewer see to trust it?
4. What happens when the input is absent, stale, or contradictory?
5. Does the feature belong in simulation, a future MVP, or later production?
6. Who owns the rule, metric, source, and approval?

## Prioritisation

Prioritise features that improve:

- correctness of voyage economics;
- explainability and audit trace;
- repeatability of scenario/Gate logic;
- safe handling of missing/uncertain data;
- mentor review speed and quality.

Deprioritise UI polish, integrations, ML, and automation of execution until simulation logic is accepted.

## Maturity rule

```text
Simulation foundation
-> Iteration 1..N
-> Final Simulation Validation
-> MVP consideration
```

There is no fixed number of iterations. MVP is a separate decision after the mentor accepts that the logic pipeline is sufficiently hardened through representative, edge, and failure cases.

