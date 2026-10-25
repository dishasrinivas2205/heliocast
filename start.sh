#!/usr/bin/env bash
# HelioCast-L1 Full-Stack Launcher
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "========================================================================"
echo " ☀️  HELIOCAST-L1: FULL-STACK UNIFIED RUNNER  ☀️"
echo "========================================================================"

# Auto-detect python
if [ -f "/Users/disha/venv/bin/python3" ]; then
    PYTHON_BIN="/Users/disha/venv/bin/python3"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
else
    PYTHON_BIN="python"
fi

echo "[*] Python interpreter: $($PYTHON_BIN --version)"
echo "[*] Node environment:   $(node -v)"
echo "[*] Starting Backend (port 8000) & Frontend (port 5173)..."
echo ""

npm run dev
