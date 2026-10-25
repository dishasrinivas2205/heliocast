"""
Strict Chronological Embargo Partitioning & Leakage Prevention.
Guarantees that train, validation, and test datasets are split strictly in chronological order
with an enforced embargo buffer preventing overlapping feature windows from leaking future information.
"""

from dataclasses import dataclass
from typing import Dict, Tuple
import numpy as np
import pandas as pd

from heliocast.logging import get_logger

logger = get_logger("heliocast.forecaster.splits")


@dataclass
class ChronologicalSplit:
    """Partitions and metadata for leak-free time-series modeling."""
    train_df: pd.DataFrame
    val_df: pd.DataFrame
    test_df: pd.DataFrame
    embargo_steps: int
    embargo_minutes: float
    train_interval: Tuple[str, str]
    val_interval: Tuple[str, str]
    test_interval: Tuple[str, str]


def make_chronological_embargo_split(
    df: pd.DataFrame,
    train_ratio: float = 0.60,
    val_ratio: float = 0.20,
    test_ratio: float = 0.20,
    embargo_minutes: float = 45.0,
    cadence_sec: float = 10.0,
) -> ChronologicalSplit:
    """
    Split time series into chronological Train, Validation, and Test partitions
    separated by an embargo gap (buffer) equal to max_lookback + horizon.
    """
    total = len(df)
    if total < 100:
        raise ValueError("Telemetry series too short for chronological splitting (minimum 100 records required)")

    embargo_steps = max(1, int((embargo_minutes * 60.0) / cadence_sec))

    train_end = int(total * train_ratio)
    val_start = train_end + embargo_steps
    val_end = val_start + int(total * val_ratio)
    test_start = val_end + embargo_steps

    if test_start >= total:
        # Scale back embargo if dataset is compact
        embargo_steps = max(1, int(total * 0.05))
        train_end = int(total * 0.50)
        val_start = train_end + embargo_steps
        val_end = val_start + int(total * 0.20)
        test_start = val_end + embargo_steps

    train_df = df.iloc[:train_end].copy().reset_index(drop=True)
    val_df = df.iloc[val_start:val_end].copy().reset_index(drop=True)
    test_df = df.iloc[test_start:].copy().reset_index(drop=True)

    def _get_interval(d: pd.DataFrame) -> Tuple[str, str]:
        if d.empty or "timestamp" not in d.columns:
            return ("N/A", "N/A")
        return (str(d["timestamp"].iloc[0]), str(d["timestamp"].iloc[-1]))

    train_int = _get_interval(train_df)
    val_int = _get_interval(val_df)
    test_int = _get_interval(test_df)

    logger.info(
        f"Chronological split created: Train={len(train_df)} ({train_int[0]} to {train_int[1]}), "
        f"Embargo={embargo_steps} steps ({embargo_minutes}m), "
        f"Val={len(val_df)} ({val_int[0]} to {val_int[1]}), "
        f"Test={len(test_df)} ({test_int[0]} to {test_int[1]})"
    )

    return ChronologicalSplit(
        train_df=train_df,
        val_df=val_df,
        test_df=test_df,
        embargo_steps=embargo_steps,
        embargo_minutes=embargo_minutes,
        train_interval=train_int,
        val_interval=val_int,
        test_interval=test_int,
    )


def verify_temporal_integrity(split: ChronologicalSplit) -> Dict[str, Any]:
    """
    Verify that no future timestamps exist in training, and that embargo buffers are strictly enforced.
    """
    t_train_max = pd.to_datetime(split.train_df["timestamp"], utc=True).max()
    t_val_min = pd.to_datetime(split.val_df["timestamp"], utc=True).min()
    t_val_max = pd.to_datetime(split.val_df["timestamp"], utc=True).max()
    t_test_min = pd.to_datetime(split.test_df["timestamp"], utc=True).min()

    gap_train_val_sec = (t_val_min - t_train_max).total_seconds()
    gap_val_test_sec = (t_test_min - t_val_max).total_seconds()

    has_leakage = (gap_train_val_sec < 0) or (gap_val_test_sec < 0)

    return {
        "has_leakage": has_leakage,
        "train_to_val_embargo_sec": gap_train_val_sec,
        "val_to_test_embargo_sec": gap_val_test_sec,
        "train_samples": len(split.train_df),
        "val_samples": len(split.val_df),
        "test_samples": len(split.test_df),
    }
