#!/usr/bin/env bash
set -e

echo "========================================================================"
echo " ☀️  HELIOCAST-L1: ISRO ADITYA-L1 SOLAR FLARE SYSTEM DEMO LAUNCHER  ☀️ "
echo "========================================================================"

# Locate python
if [ -f "/Users/disha/venv/bin/python" ]; then
    PYTHON="/Users/disha/venv/bin/python"
else
    PYTHON="python3"
fi

echo "[*] Using Python: $($PYTHON --version)"
echo "[*] Executing HelioCast-L1 Scientific Pipeline Demo..."
$PYTHON run_demo.py

echo ""
echo "========================================================================"
echo " To launch Mission Control Dashboard UI, run:"
echo "     $PYTHON -m streamlit run frontend/app.py"
echo " To launch FastAPI Backend Server, run:"
echo "     $PYTHON -m uvicorn heliocast.api.app:app --reload --port 8000"
echo "========================================================================"
