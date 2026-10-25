#!/usr/bin/env python3
"""
HelioCast-L1 Quick Demo Launcher
Executes the full pipeline: Ingestion -> Precursor Forecast -> Dual Nowcast -> Master Catalog Fusion.
"""

import sys
from pathlib import Path

# Ensure package in path
sys.path.insert(0, str(Path(__file__).parent))

from heliocast.cli import run_pipeline

if __name__ == "__main__":
    run_pipeline(hours=4.0, cadence=10.0)
