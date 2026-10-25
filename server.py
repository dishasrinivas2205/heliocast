#!/usr/bin/env python3
"""
Root entrypoint delegating directly to backend/server.py.
Ensures 100% compatibility with root scripts, Docker, and cloud runners.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.server import main

if __name__ == "__main__":
    main()
