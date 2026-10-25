#!/usr/bin/env python3
"""
HelioCast-L1 Standalone Backend Server Entrypoint.
Starts the FastAPI application with live Aditya-L1 telemetry ingestion,
cross-spectral solar flare nowcasting, probabilistic precursor forecasting,
FTS5 SQLite catalog queries, and API key management.
"""

import os
import sys
from pathlib import Path

# Ensure project root is in sys.path
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Detect local user venv if dependencies not in system path
VENV_PYTHON = Path("/Users/disha/venv/bin/python3")
try:
    import fastapi
    import uvicorn
except ImportError:
    if VENV_PYTHON.exists() and sys.executable != str(VENV_PYTHON):
        os.execv(str(VENV_PYTHON), [str(VENV_PYTHON)] + sys.argv)
    else:
        raise

# Load environment variables
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

import uvicorn
from heliocast import __version__


def main():
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("PORT", os.getenv("API_PORT", "8000")))
    env = os.getenv("HELIOCAST_ENV", "development")
    reload = env == "development" and os.getenv("API_RELOAD", "true").lower() in ("true", "1", "yes")

    print("\n" + "=" * 76)
    print(f" ☀️  HELIOCAST-L1 v{__version__} — ISRO ADITYA-L1 SCIENTIFIC BACKEND SERVER")
    print("=" * 76)
    print(f" • REST API Base:        http://{host}:{port}/api/v1")
    print(f" • Interactive API Docs: http://{host}:{port}/docs")
    print(f" • Static Cockpit UI:    http://{host}:{port}/")
    print(f" • Environment:          {env}")
    print(f" • Master Database:      {os.getenv('DATABASE_PATH', 'data/catalog/aditya_flares.db')}")
    print("=" * 76 + "\n")

    uvicorn.run(
        "heliocast.api.app:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
        access_log=True,
    )


if __name__ == "__main__":
    main()
