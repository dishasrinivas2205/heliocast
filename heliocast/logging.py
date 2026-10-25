"""
Structured Logging Subsystem for HelioCast-L1.
Adheres to strict ISO-8601 UTC timestamps, contextual telemetry tags,
and consistent log formatting across pipeline, models, and servers.
"""

from datetime import datetime, timezone
import logging
import sys
from typing import Any, Dict, Optional


class StructuredFormatter(logging.Formatter):
    """
    Format logs with UTC ISO timestamp, module name, severity, and key-value extra fields.
    """

    def format(self, record: logging.LogRecord) -> str:
        # Timezone-aware UTC timestamp
        utc_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        level = record.levelname.ljust(8)
        name = record.name

        base = f"[{utc_ts}] [{level}] [{name}] {record.getMessage()}"

        extra_fields = getattr(record, "extra_fields", None)
        if extra_fields and isinstance(extra_fields, dict):
            field_str = " | ".join(f"{k}={v}" for k, v in extra_fields.items())
            return f"{base} | {field_str}"

        return base


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Obtain a configured logger instance with structured formatting.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredFormatter())
        logger.addHandler(handler)
        logger.propagate = False

    return logger
