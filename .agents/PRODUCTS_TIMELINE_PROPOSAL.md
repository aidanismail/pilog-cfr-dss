# Proposed Product Timeline Alignment

This proposal supersedes the maturity/timeline sections of `PRODUCTS.MD` after approval.

## Route-agnostic product rule

Origin and destination are manual case inputs from the selected Excel/CSV dataset. The product must not hardcode a route, port, country, or route-specific commercial/operational rule. Missing route-specific input is a data-quality issue, not a reason to reuse another route's values.

## Product maturity timeline

```text
Simulation foundation
-> Iteration 1 review
-> Iteration 2
-> Iteration 3 ... Iteration N
-> Final Simulation Validation
-> MVP build
-> MVP validation
-> Production consideration (separate approval)
```

### Simulation foundation

Build a safe, repeatable pipeline with local/manual inputs. Every result is advisory-only and designed to make data, formula, and rule gaps visible.

### Iteration 1 through Iteration N

```text
plan
-> bounded task execution
-> deterministic tests/evidence
-> mentor review
-> reflection and decision log
-> iteration-state update
-> next iteration
```

There is no predefined final iteration. The simulation stage continues until the mentor approves that the pipeline logic, business definitions, calculation boundaries, controls, and outputs are sufficiently hardened.

### Final Simulation Validation

Run the mentor-approved pipeline against representative, edge, and failure cases. Verify traceability, safe failure, formula/rule versions, and review evidence.

Possible result:

```text
ready_for_mvp_design
needs_more_iterations
blocked_by_data_or_policy
```

### MVP build

Start MVP only after Final Simulation Validation is accepted. MVP turns approved simulation logic into a controlled user workflow; it does not silently change unfinished formula or policy assumptions.

## Final simulation validation readiness

- mentor-approved formula and cost boundary;
- approved route-agnostic data contract and variable map;
- Gate 1/Gate 2 rules tested through multiple iterations;
- deterministic modules with tests and traceable source/unit/freshness inputs;
- representative, edge, and failure cases reproduced;
- human approval/override design;
- mentor accepts the logic pipeline for MVP design.

