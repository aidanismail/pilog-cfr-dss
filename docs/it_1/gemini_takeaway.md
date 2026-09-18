# Agent Handover: Maritime Decision Support System (DSS) - Iteration 2.0

## 1. System Objective
**Previous State:** The DSS functioned as a static arithmetic calculator, translating fixed voyage variables into a 4 scenarios simple business decision.
**Target State:** The DSS must now function as a dynamic, constraint-based optimization engine. It must validate physical feasibility and environmental compliance *before* calculating financial returns, utilizing all 62 dataset variables.

## 2. Execution Order & Logical Gates
The agent must reconstruct the processing pipeline in the following sequence:

### PHASE 1: Physical & Operational Gatekeeping (Pass/Fail)
*Do not execute financial math until the voyage passes these physical checks.*
*   **Draft Limits (Variables 15, 18, 42, 43):**
    *   Calculate required draft dynamically using Deadweight (DWT), Cargo Quantity (DWCC), and Tonnes per Centimeter (TPC).
    *   *Logic Check:* Does calculated voyage draft exceed the destination port's maximum draft? (e.g., East Coast India river ports). If YES -> Reject/Flag Voyage.
*   **Volumetric Capacity (Variables 1, 47, 48):**
    *   Calculate cargo volume: `DWCC * Cargo Stowage Factor (CBM/MT)`.
    *   *Logic Check:* Does cargo volume exceed the vessel's Grain/Bale capacity? If YES -> Reduce DWCC to max cubic capacity.
*   **Gear Constraints (Variables 49-54):**
    *   *Logic Check:* If destination port API flags "Un-geared terminal", does the vessel possess its own Cranes and Grabs? If NO -> Reject/Flag Voyage.

### PHASE 2: Dynamic Optimization & API Hooks
*Replace static baseline assumptions with algorithmic optimization.*
*   **Speed Optimization Calculus (Variables 55-62):**
    *   *Instruction:* Stop using static speeds (Variables 6 & 7). 
    *   *Logic:* Iterate through the performance curves (11 to 14 knots). Plot the marginal savings in fuel consumption against the daily opportunity cost (Hire Rate - Variable 28). Select the speed that yields the highest absolute profit, not just the fastest transit.
*   **Port Power Load Factor (Variables 12, 13, 14):**
    *   *Instruction:* Do not use a static 0.7 (70%) load factor. If API indicates the port uses shore cranes, override the ship's auxiliary engine load factor to 0.2 (20%) to accurately reduce projected port diesel costs.

### PHASE 3: Environmental Compliance Routing
*   **Bunker Fuel Pricing (Variables 38, 39, 40):**
    *   *Logic Check:* Is `Scrubber fitted = Yes`? 
    *   If YES -> Ping API for High Sulfur Fuel Oil (HSFO) price.
    *   If NO -> Ping API for Very Low Sulfur Fuel Oil (VLSFO) price.
*   **CII / Emissions Projection:**
    *   *Instruction:* Run the selected fuel consumption rate through IMO Carbon Intensity Indicator (CII) formulas. Flag the voyage if the required fuel burn pushes the vessel's annual rating into non-compliant "D" or "E" territory.

### PHASE 4: Core TCE Calculation Pipeline
*Execute the standard financial math using optimized variables from Phases 1-3.*
1.  **Total Voyage Days:** Laden Days + Ballast Days + Port Days
2.  **Voyage Costs:** FO Cost (Sea) + DO Cost (Sea + Port) + Local Port Costs (Convert to USD)
3.  **Net Revenue:** (DWCC * Freight Rate) * (1 - Commission Rates)
4.  **TCE:** (Net Revenue - Voyage Costs) / Total Voyage Days

### PHASE 5: Decision Matrix & Benchmarking
*Output final system recommendation based on the following logic:*
*   **IF** TCE < Open Market Hire Rate **AND** TCE < Daily Cost: `Recommend FOB Only (Reject Freight Risk)`
*   **IF** TCE > Open Market Hire Rate: `Recommend CFR (Arbitrage Opportunity via 3rd Party Tonnage)`
*   **IF** TCE > Daily Cost: `Recommend CFR (Utilize Owned Tonnage)`
*   **Benchmark Output:** Compare the final TCE against the Baltic Supramax Index (Variable 37) adjusted for vessel size (58k DWT vs 63.5k DWT) to report commercial alpha.

---
**End of Handover Document. Agent to parse and update decision trees accordingly.**