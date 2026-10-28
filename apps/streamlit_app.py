"""Run from repository root: python -m streamlit run apps/streamlit_app.py."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pilog_cfr_dss.ui.views import render

# Test-only storage override; input templates always come from the repository.
render(ROOT, Path(os.environ["PILOG_UI_OUTPUT_ROOT"]) if os.environ.get("PILOG_UI_OUTPUT_ROOT") else None)
