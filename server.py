#!/usr/bin/env python3
"""
HelioCast-L1 Scientific Backend Server Entrypoint.
Starts the FastAPI application with live Aditya-L1 telemetry ingestion,
cross-spectral solar flare nowcasting, probabilistic precursor forecasting,
and API key management.
"""

import os
import sys
from pathlib import Path

# Automatically ensure HelioCast project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

import uvicorn
from heliocast import __version__


def main():
    host = os.getenv("API_HOST", "0.0.0.0")
    # Render injects PORT env var; fall back to API_PORT, then 8000
    port = int(os.getenv("PORT", os.getenv("API_PORT", "8000")))
    # Disable reload in production (Render sets HELIOCAST_ENV=production)
    env = os.getenv("HELIOCAST_ENV", "development")
    reload = env == "development" and os.getenv("API_RELOAD", "true").lower() in ("true", "1", "yes")

    print("\n" + "=" * 76)
    print(f" ☀️  HELIOCAST-L1 v{__version__} — ISRO ADITYA-L1 SCIENTIFIC BACKEND SERVER")
    print("=" * 76)
    print(f" • REST API Base:        http://{host}:{port}/api/v1")
    print(f" • Interactive API Docs: http://{host}:{port}/docs")
    print(f" • Static Cockpit UI:    http://{host}:{port}/")
    print(f" • Environment:          {env}")
    print(f" • Telemetry Cadence:    {os.getenv('TELEMETRY_CADENCE_SEC', '10')}s")
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
