---
name: pilog-voyage-economics
description: Model dry-bulk voyage economics for PILOG CFR scenarios with explicit price objects, owned-versus-chartered cost boundaries, deterministic calculations, and evidence-driven assumptions.
---

# PILOG Voyage Economics

Use this skill for freight economics, voyage cost, chartering, owned versus chartered tonnage, fuel, commission, contribution, TCE, or maritime decision interpretation.

## Domain focus

The mentor context prioritises dry-bulk chartering, freight contract negotiation, voyage performance, post-fixture execution, and freight strategy. Model the commercial question as:

> After operational constraints and relevant costs, does this arrangement create acceptable economic value for PILOG?

Do not use a higher CFR selling price as proof of a better decision.

## Price objects must remain distinct

```text
Index                 = approved commodity/market reference
Alpha                 = approved commercial adjustment to Index
FOB price             = Index + Alpha
Freight selling rate  = freight amount charged/offered to customer
Freight cost          = relevant cost to provide freight
Contribution          = selling rate - relevant freight cost
TCE                   = a USD/day voyage-performance metric; use only with approved cost boundary
```

Never treat these as interchangeable. Confirm the business meaning of each source field before coding.

## Required economics discipline

- Use deterministic Python `Decimal` functions; LLMs never supply authoritative numbers.
- Declare unit, currency, quantity basis, source, as-of date, and scenario applicability.
- Define the cost boundary before computing contribution or TCE.
- Avoid double counting: every adjustment/cost component has one economic mechanism and one owner.
- Separate owned/operated vessel economics from chartered-vessel economics. Do not assume hire, running cost, bunker, commission, or other voyage cost are cumulative without mentor confirmation.
- Return `HOLD_DEFINITION_REQUIRED` when the meaning of Freight Rate, cost allocation, or commission basis is unresolved.

## Minimum deterministic relationships

Only implement a relationship when its inputs/definitions are approved:

```text
sea days = distance / (speed * 24)
port days = cargo quantity / handling rate
fuel quantity = applicable days * consumption rate
fuel cost = fuel quantity * fuel price
freight contribution = freight selling rate - relevant freight cost
```

TCE, benchmark alpha, environmental compliance, and advanced optimisation are later layers unless their data contract and business policy are approved.

