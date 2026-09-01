#!/usr/bin/env bash
# One command: build the corpus, produce the evidence pack, close one defect
# loop, then open the prototype. No API key and no network required.
set -euo pipefail
cd "$(dirname "$0")"

PY="${PY:-python3}"
if [ -x .venv/bin/python ]; then PY=.venv/bin/python; fi

echo "== 1/4  generating the simulated corpus"
$PY data/generate.py
$PY -m data.holdout

echo
echo "== 2/4  measuring detection quality, latency and cost"
$PY scripts/run_eval.py

echo
echo "== 3/4  closing one defect loop end to end"
$PY scripts/run_demo.py

echo
echo "== 4/4  starting the prototype at http://localhost:8501"
exec $PY -m streamlit run app/streamlit_app.py
