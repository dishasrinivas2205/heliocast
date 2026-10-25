"""
Telemetry Data Schema and Quality Bitmask Definitions for Aditya-L1.
Preserves physical measurement integrity, timestamps, and instrument flags.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import IntFlag
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd


class QualityFlag(IntFlag):
    """
    Quality bitmask flags for Aditya-L1 Level-1 telemetry.
    Zero indicates strictly nominal science observation.
    """
    NOMINAL = 0
    CALIBRATION_MODE = 1 << 0       # Internal detector calibration / test pattern
    ECLIPSE_OCCULTATION = 1 << 1    # Sun-spacecraft line of sight blocked or occulted
    PARTICLE_SPIKE = 1 << 2         # High-energy cosmic-ray or solar energetic particle glitch
    TELEMETRY_GAP = 1 << 3          # Missing packet or cadence drop
    SATURATION = 1 << 4             # Pulse pile-up or detector saturation
    SAA_OR_MAGNETIC_ANOMALY = 1 << 5 # Spacecraft passing through high background radiation zone


@dataclass
class TelemetryRecord:
    """Individual time step observation from Aditya-L1 payloads."""
    timestamp: datetime
    solexs_flux: float              # Soft X-ray (1-22 keV) count rate (counts/sec)
    helios_flux: float              # Hard X-ray (10-150 keV) count rate (counts/sec)
    solexs_quality: int = QualityFlag.NOMINAL
    helios_quality: int = QualityFlag.NOMINAL
    hardness_ratio: float = 0.0     # helios_flux / max(solexs_flux, 1e-3)
    flare_in_progress: bool = False
    ground_truth_class: Optional[str] = None


def parse_aditya_timestamp(val: Any) -> datetime:
    """
    Robust timestamp parser for ISRO Aditya-L1 timestamps.
    Handles ISO strings, pandas Timestamps, and numeric epoch/MET seconds.
    Always returns timezone-aware UTC datetime.
    """
    if isinstance(val, datetime):
        if val.tzinfo is None:
            return val.replace(tzinfo=timezone.utc)
        return val.astimezone(timezone.utc)

    if isinstance(val, (int, float, np.integer, np.floating)):
        # If float value represents seconds since 2024-01-01 (MET) or Unix epoch
        if val > 1_000_000_000:  # Standard Unix epoch timestamp
            return datetime.fromtimestamp(float(val), tz=timezone.utc)
        else:
            # Aditya-L1 Mission Elapsed Time reference: 2023-09-02T06:20:00Z (Launch date)
            base = datetime(2023, 9, 2, 6, 20, 0, tzinfo=timezone.utc)
            return datetime.fromtimestamp(base.timestamp() + float(val), tz=timezone.utc)

    try:
        dt = pd.to_datetime(val)
        if dt.tzinfo is None:
            return dt.tz_localize("UTC").to_pydatetime()
        return dt.tz_convert("UTC").to_pydatetime()
    except Exception as exc:
        raise ValueError(f"Unable to parse timestamp '{val}': {exc}") from exc
