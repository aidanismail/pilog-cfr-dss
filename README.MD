PILOG CFR DSS

Run: venv/Scripts/python.exe -m streamlit run apps/streamlit_app.py

App entry: apps/streamlit_app.py
UI: src/pilog_cfr_dss/ui/
Workflow: src/pilog_cfr_dss/application/
Current engine: src/pilog_cfr_dss/calculations/, decisions/, orchestration/, validation/ and reporting/. The engine uses descriptive names: orchestration/case_evaluation.py, calculations/voyage_economics.py, calculations/freight_pricing.py, calculations/tender_pricing.py, and reporting/commercial_brief.py.
Inputs: data/raw/ and data/processed/. The OD distance workbook is in data/raw/.
Current plan: docs/it_5/ITERATION_05_PLAN.md
Active CLI: scripts/refresh_market_inputs.py and scripts/run_market_simulation.py
Tests: venv/Scripts/python.exe -m unittest discover -s tests -q

This is an advisory simulation, not an automated award or transaction system.
