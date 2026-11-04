PILOG CFR DSS

Run: venv/Scripts/python.exe -m streamlit run apps/streamlit_app.py

App entry: apps/streamlit_app.py
UI: src/pilog_cfr_dss/ui/
Workflow: src/pilog_cfr_dss/application/
Current engine: src/pilog_cfr_dss/calculations/, decisions/, orchestration/, validation/ and reporting/. The engine uses descriptive names: orchestration/case_evaluation.py, calculations/voyage_economics.py, calculations/freight_pricing.py, calculations/tender_pricing.py, and reporting/commercial_brief.py.
Inputs: data/raw/ and data/processed/. Active I5 reads voyage defaults without OD; sea distance uses Searoute or explicit manual input. Historical CLI/replay retains the OD contract.
Current plan: docs/it_5/RENCANA_PENYESUAIAN_INPUT_VOYAGE.md
Active CLI: scripts/refresh_market_inputs.py and scripts/run_market_simulation.py
Tests (PowerShell): $env:PYTHONPATH='src'; venv/Scripts/python.exe -m unittest discover -s tests -t . -q

I5: one editable input table, TC Rates from Fearnpulse, allowance-based capacity screen, voyage indication, TCE, break-even freight and fixed-freight sensitivity. Tender and commercial brief remain hidden in the active UI. Full-voyage cost is allocated to the entered cargo; no part-cargo allocation is implied.

Download an editable case package from the sidebar and import it after refresh. Results are recalculated from the restored inputs; there is no permanent shared case list. Server working files and market cache are temporary. Runtime market data is written to outputs/market_cache, never to source seeds.

Market reports remain historical PDF assessments. Missing regional comparables are shown as unavailable. Data quality enrichment, terminal/laycan readiness, charter economics, RBAC and live transactions require separate domain scope.

This is an advisory simulation, not an automated award or transaction system.
