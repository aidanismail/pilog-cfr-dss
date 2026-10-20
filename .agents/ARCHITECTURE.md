# Modular Architecture and Directory Workflow

## Purpose

Iteration 1 proved the pipeline using standalone scripts. Iteration 2 reorganises logic into small, deterministic modules. The nine standalone scripts were removed after replacement tests passed, per the user's cleanup approval; their tracked versions remain recoverable in Git history. Generated Iteration 1 root outputs and older Iteration 2 run folders were later removed during the approved repository cleanup. One complete revised Iteration 2 run remains as example evidence.

The architecture has one direction of dependency:

```text
data and policy inputs
-> canonical models
-> validation and constraints
-> deterministic calculations
-> scenarios
-> gates and recommendation
-> reporting / review artefacts
-> human decision
```

No reporting, UI, prompt, Excel, or LLM component may contain authoritative business formulas.

## Target directory structure

```text
pilog-cfr-dss/
|
|-- .agents/                         # Agent instructions, state, plans, reviews
|   |-- 00_READ_CURRENT.md
|   |-- AGENTS.md
|   |-- PRODUCTS.MD
|   |-- ARCHITECTURE.md
|   |-- ITERATION_STATE.json
|   |-- DECISIONS.md
|   |-- reviews/
|   |-- tasks/
|   `-- templates/
|
|-- data/
|   |-- raw/                         # Workbook sumber/audit mentor; pertahankan isinya
|   `-- processed/                   # Input siap-baca I3, policy/katalog, dan fixture regresi I2
|
|-- src/
|   `-- pilog_cfr_dss/
|       |-- __init__.py
|       |-- models/                  # Typed input/output contracts and units
|       |-- validation/              # Data quality, route, and evidence checks
|       |-- calculations/            # Pure Decimal calculation functions only
|       |-- scenarios/               # Scenario construction from one Case snapshot
|       |-- decisions/               # Gate 1, Gate 2, reason codes, recommendation
|       |-- reporting/               # Decision brief and learning/report generators
|       `-- orchestration/           # Explicit pipeline sequencing; no business math
|
|-- scripts/
|   |-- build_variable_workbook.py   # Learning artefact generator, not pricing engine
|   `-- run_iteration_02.py          # Thin command-line entry point
|
|-- tests/
|   |-- unit/                        # One module/function behaviour per test
|   |-- integration/                 # End-to-end simulation pipeline tests
|   `-- fixtures/                    # Small safe/dummy input cases for tests
|
|-- outputs/
|   |-- runs/<run_id>/               # Generated pipeline evidence; one curated example tracked
|   |-- learning/                    # Generated Excel for intern/mentor learning
|   `-- reviews/                     # Generated review evidence, not agent policy
|
|-- docs/
|   `-- it_1/                        # Historical source feedback from Iteration 1
|
`-- app/                             # Empty until Final Simulation Validation permits MVP UI work
```

## Responsibility of each code layer

| Layer | May do | Must not do |
|---|---|---|
| `models` | Define dataclasses/types, units, validation result structures | Calculate business values or read files |
| `validation` | Validate presence, type, unit, source, freshness, route evidence | Choose commercial action |
| `calculations` | Calculate capacity, days, fuel, cost, economics with `Decimal` | Read CLI args, write files, call LLM, make approval decisions |
| `scenarios` | Build alternatives from the same validated case snapshot | Invent inputs or compare incompatible snapshots |
| `decisions` | Apply approved rules, emit status/reason codes/recommendation | Recalculate hidden economics or execute action |
| `reporting` | Render deterministic outputs as Markdown/JSON/learning Excel | Alter calculation results or policy |
| `orchestration` | Sequence modules and persist immutable run artefacts | Hide errors or contain business formulas |
| `scripts` | Parse explicit command inputs and invoke orchestration | Hold reusable business logic |

## Calculation-module workflow

```text
CaseSnapshot
-> validate_case()
-> validate_route_inputs()
-> calculate_capacity()              # only when supported by data contract
-> calculate_voyage_days()
-> calculate_fuel_consumption()
-> calculate_fuel_cost()
-> calculate_commission()
-> calculate_voyage_cost()
-> calculate_freight_economics()
-> build_scenarios()
-> evaluate_gate_1()
-> evaluate_gate_2()
-> recommend_action()
-> build_decision_brief()
```

Any missing required dependency halts its dependent calculation with a structured status:

```text
PASS | WARN | HOLD_DATA_ISSUE | HOLD_DEFINITION_REQUIRED | BLOCK
```

## Route-agnostic contract

The selected dataset/manual input owns the route. Code must not branch on port/country names.

```text
loading_port + discharging_port
-> selected route inputs
-> validated route-specific evidence
-> calculation or HOLD
```

For example, distance, port time, tariff, port restriction, and terminal condition are data, not code constants. If unavailable, the result is an explicit HOLD; the system must not borrow a value from another route.

## Migration from Iteration 1

The standalone scripts have been replaced by tested modules and removed from the worktree with user authorization. Their historical source is recoverable from Git; prior output artefacts were not deleted. Do not recreate a `legacy/` script tree. Preserve useful input/output semantics where possible, but do not preserve known incorrect logic such as quality `BLOCK` coexisting with Gate 1 eligibility. See `.agents/reviews/ITERATION_02.md` for task, formula, test, and review evidence.

## Output workflow

```text
one pipeline run
-> unique run_id
-> input snapshot copy/hash
-> validation report
-> calculation trace
-> scenario comparison
-> gate evidence
-> recommendation / safe hold
-> decision brief
-> review record
```

Generated outputs are evidence. They must not become inputs for a new run unless explicitly versioned and approved as a snapshot/reference source.

## First directory changes allowed in Iteration 2

The following are safe now because they contain no unapproved business logic:

```text
src/pilog_cfr_dss/
src/pilog_cfr_dss/models/
src/pilog_cfr_dss/validation/
src/pilog_cfr_dss/calculations/
src/pilog_cfr_dss/scenarios/
src/pilog_cfr_dss/decisions/
src/pilog_cfr_dss/reporting/
src/pilog_cfr_dss/orchestration/
tests/unit/
tests/integration/
tests/fixtures/
data/raw/
data/processed/
outputs/runs/
outputs/learning/
outputs/reviews/
```

Do not start adding calculation logic until I2-T01 variable mapping is reviewed.

## Penataan data 20 Oktober 2026

Struktur data aktif hanya `raw/` dan `processed/`; folder kosong `cases/`, `reference/`, `learning/`, dan `snapshots/` di bawah `data/` dihapus. CLI, default policy pada orchestrator, tes, dan dokumentasi memakai path `data/processed/`. CSV, JSON, dan workbook tidak ditulis ulang. Input historis I2 tetap diperlukan oleh regresi dan tes lineage I3; generated learning workbook dan snapshot eksekusi tetap berada di `outputs/`, bukan `data/`.

`processed` tidak berarti sumber sudah disahkan untuk transaksi. Teks lineage historis di CSV I3 dipertahankan; `source_reference = data/dataset_ready.csv` menunjuk sumber yang kini dipindah ke `data/processed/dataset_ready.csv`. Rumus/gate dan perbaikan bisnis hasil audit belum diimplementasikan oleh penataan direktori ini.
