# Shipping DSS Domain Knowledge Handover

## Project Context

The project goal is to develop a Decision Support System (DSS) for PT Pupuk Logistik Indonesia (PT PLI) to support shipment bid decisions.

The DSS evaluates whether a shipment opportunity should be handled as:

1. FOB only
2. CFR using owned vessel
3. CFR using chartered vessel
4. No Bid

The system is not intended to replace human commercial judgement. It should provide transparent economic analysis and supporting information for decision makers.

The next iteration should focus on improving domain correctness, data modeling, assumptions, and explainability.

---

# 1. Core Business Understanding

## Shipping Decision Problem

A shipment opportunity is not evaluated only from selling price.

The company needs to consider:

- cargo economics
- freight exposure
- vessel availability
- voyage cost
- operational feasibility
- risk exposure

A high revenue shipment does not necessarily mean a profitable shipment.

The important business question:

> "After considering all expected costs and operational constraints, does accepting this shipment create acceptable economic value?"

---

# 2. Important Shipping Concepts

## FOB (Free On Board)

FOB means the seller's responsibility generally ends when cargo is loaded onto the vessel.

For this DSS:

FOB scenario mainly evaluates:

- cargo purchase cost
- selling price
- handling cost

Freight exposure is not included.

---

## CFR (Cost and Freight)

CFR means the seller is responsible for arranging and paying ocean freight to the destination port.

Important:

CFR economics consist of:

- cargo value
- freight cost
- operational cost
- additional risks

Freight is not a simple fixed value because it depends on:

- vessel type
- route
- bunker price
- voyage duration
- market condition

---

# 3. Important Domain Insight

Do not compare options only by revenue.

The correct comparison should consider:

## Profitability

Example:

A CFR shipment may have higher revenue than FOB.

However:

- freight cost may remove the margin
- bunker prices may increase
- vessel availability may create additional cost

Therefore:

Higher selling price ≠ better decision.

---

# 4. Required Data Categories

## Shipment Data

Purpose:
Describe the commercial opportunity.

Important fields:

- shipment ID
- origin port
- destination port
- cargo type
- cargo quantity
- customer price
- FOB cargo cost
- laycan period

---

## Route Data

Purpose:
Understand voyage characteristics.

Important fields:

- origin location
- destination location
- sailing distance
- port information
- loading conditions
- discharge conditions

---

## Vessel Data

Purpose:
Compare owned vessel vs charter vessel.

Important fields:

- vessel type
- vessel capacity
- fuel consumption
- ownership status
- operating cost
- charter rate

---

## Market Data

Purpose:
Capture external cost changes.

Important fields:

- bunker price
- charter market rate
- exchange rate (optional)

---

# 5. Variables Classification

## Mandatory Variables

These directly influence commercial decisions.

### Shipment

- Cargo quantity
- Selling price
- Cargo cost
- Origin
- Destination
- Cargo type
- Laycan

### Route

- Distance
- Port cost
- Voyage duration

### Vessel

- Capacity
- Fuel consumption
- Ownership type
- Charter rate
- Operating cost

### Market

- Bunker price

---

# 6. Variables That Are Optional / Future Enhancement

These should not complicate the first MVP.

## Advanced Risk Variables

Examples:

- delay probability
- weather condition
- port congestion
- demurrage probability

Useful for:

- risk scoring
- scenario simulation

---

## Hedging Variables

Examples:

- Freight Forward Agreement (FFA)
- hedge ratio
- commodity futures
- FX hedge

These are relevant for freight risk management but unnecessary unless the company actively performs financial hedging.

---

## Machine Learning Variables

Possible future features:

### Cost Prediction

Input:

- historical voyages
- routes
- vessel class
- bunker prices
- charter rates

Output:

- predicted voyage cost

---

### Delay Prediction

Input:

- port congestion
- weather
- historical delays

Output:

- probability of delay

---

# 7. Important Shipping Metrics

## Freight Cost

Freight should be normalized.

A shipment comparison should usually use:

USD / MT

because cargo sizes differ.

---

## TCE (Time Charter Equivalent)

TCE is a shipping industry metric to compare voyage performance in USD/day.

Useful when comparing:

- owned vessel opportunity
- charter market opportunity

It is an advanced metric, not necessarily required for MVP.

---

# 8. Common Modeling Mistakes to Avoid

## Mistake 1:

Treating freight as a constant.

Reality:

Freight changes because of:

- bunker prices
- vessel supply
- route conditions
- market situation

---

## Mistake 2:

Ignoring vessel ownership difference.

Owned vessel:

Main cost:

- operating cost
- fuel
- maintenance

Chartered vessel:

Main cost:

- charter hire
- fuel
- port expenses

---

## Mistake 3:

Using too many maritime variables without business impact.

The DSS should prioritize:

- explainability
- maintainability
- decision usefulness

Not maximum complexity.

---

# 9. Recommended Data Model Improvements

The system should separate:

## Master Data

Rarely changes.

Examples:

- vessel information
- port information
- vessel capacity

---

## Transaction Data

Changes every shipment.

Examples:

- bid request
- cargo quantity
- customer price
- route

---

## Market Data

Changes frequently.

Examples:

- bunker price
- charter rate
- exchange rate

---

# 10. Recommended DSS Design Principles

## Explainability First

The system should answer:

"Why was this option recommended?"

Example:

Recommendation:

CFR Owned Vessel

Reasons:

- lower freight cost
- vessel available
- acceptable margin

Risks:

- bunker exposure
- delay sensitivity

---

## Human-in-the-loop

The DSS should support:

- commercial team
- operation team
- management

It should not automatically execute bidding decisions.

---

# 11. Future Enhancement Ideas

## Scenario Simulation

Allow users to test:

"What happens if bunker price increases 20%?"

"What happens if vessel delay increases 5 days?"

"What happens if charter rate increases?"

---

## Historical Learning

Use previous shipments to improve:

- cost estimation
- delay prediction
- bid success probability

Possible models:

- Linear Regression
- Random Forest
- XGBoost

---

# 12. Final Scope Recommendation

## MVP

Include:

- FOB evaluation
- CFR owned vessel evaluation
- CFR charter vessel evaluation
- cost breakdown
- profit comparison
- recommendation explanation

## Phase 2

Add:

- risk scoring
- sensitivity analysis
- scenario simulation

## Phase 3

Add:

- machine learning prediction
- historical optimization
- automated recommendations

---

# Key Takeaway

The system is not a maritime optimization engine.

It is a business DSS.

The objective is:

"Convert shipping domain knowledge into a transparent decision-support tool that helps PT PLI decide whether a shipment opportunity should be accepted and under what commercial arrangement."

The next iteration should prioritize:

1. Correct domain assumptions
2. Clean data modeling
3. Explainable calculations
4. Practical business usage
