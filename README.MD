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

Active cases use chartered vessels (I5-CHARTER.1). Hire/day defaults to USD 13,000/day from the approved historical example and is editable in the input table; it is independent of the Fearnpulse TC reference used to form indicative freight. Owned-vessel running cost is excluded. Changing class or refreshing market data does not overwrite Hire/day. TCE = (net freight revenue - voyage expenses) / total voyage days; estimated surplus additionally deducts Hire/day x hire days. Baseline hire days equal the approved one-way voyage duration including loading, sailing, discharge and waiting.

New charter packages use PILOG-CASE.2 and preserve Hire/day and its source. Historical owned packages remain replayable through the engine and retain their original meaning; the active UI asks for a new case rather than silently converting running cost to hire. When updating an existing browser session, choose Kasus baru if it still contains the old owned model.

Download an editable case package from the sidebar and import it after refresh. Results are recalculated from the restored inputs; there is no permanent shared case list. Server working files and market cache are temporary. Runtime market data is written to outputs/market_cache, never to source seeds.

Market reports remain historical PDF assessments. Regional/global context is labelled with its original price basis and route; it is not automatically a comparable destination quote. Actual vessel hire quotations, full delivery/redelivery scope, data enrichment, terminal/laycan readiness, RBAC and live transactions remain outside this estimate.

This is an advisory simulation, not an automated award or transaction system.
