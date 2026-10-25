"""
Scientific Telemetry Quality Auditor for Aditya-L1.
Validates timestamp monotonicity, identifies duplicate timestamps, detects telemetry gaps,
constructs availability masks, and enforces numerical ratio guards.
"""

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from heliocast.logging import get_logger

logger = get_logger("heliocast.quality.audit")


@dataclass
class QualityAuditReport:
    """Consolidated telemetry quality audit metrics."""
    total_records: int
    is_monotonic: bool
    duplicate_count: int
    gap_count: int
    max_gap_duration_sec: float
    total_gap_duration_sec: float
    solexs_missing_count: int
    helios_missing_count: int
    solexs_availability_pct: float
    helios_availability_pct: float
    joint_availability_pct: float
    ratio_division_by_zero_prevented: int
    quality_flag_summary: Dict[str, int]


def safe_spectral_hardness_ratio(
    helios_flux: Any,
    solexs_flux: Any,
    min_sxr_threshold: float = 1.0,
    max_ratio_clip: float = 10.0,
) -> np.ndarray:
    """
    Safely compute spectral hardness ratio HXR / SXR without division by zero,
    numerical overflow, or noise floor amplification.
    """
    h = np.asarray(helios_flux, dtype=float)
    s = np.asarray(solexs_flux, dtype=float)

    invalid_mask = np.isnan(s) | np.isnan(h) | (s < min_sxr_threshold) | (h < 0.0)
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(invalid_mask, 0.0, h / np.maximum(s, min_sxr_threshold))

    return np.clip(ratio, 0.0, max_ratio_clip)


class TelemetryQualityAuditor:
    """
    Performs rigorous data quality checks on Aditya-L1 time-series observations.
    """

    def __init__(
        self,
        nominal_cadence_sec: float = 10.0,
        gap_threshold_multiplier: float = 3.0,
        min_denominator_threshold: float = 5.0,
    ):
        self.nominal_cadence_sec = nominal_cadence_sec
        self.gap_threshold_sec = nominal_cadence_sec * gap_threshold_multiplier
        self.min_denominator_threshold = min_denominator_threshold

    def audit(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, QualityAuditReport]:
        """
        Audit telemetry dataframe, add quality and availability masks,
        and generate a comprehensive audit report.
        """
        if df.empty:
            raise ValueError("Cannot audit empty dataframe")

        df_clean = df.copy()
        timestamps = pd.to_datetime(df_clean["timestamp"], utc=True)

        # 1. Monotonicity & Ordering Check
        time_diffs = timestamps.diff().dt.total_seconds()
        is_monotonic = bool((time_diffs.iloc[1:] >= 0).all()) if len(df_clean) > 1 else True

        # Sort if not monotonic
        if not is_monotonic:
            logger.warning("Timestamps are not strictly non-decreasing; sorting chronological order.")
            df_clean = df_clean.sort_values(by="timestamp").reset_index(drop=True)
            timestamps = pd.to_datetime(df_clean["timestamp"], utc=True)
            time_diffs = timestamps.diff().dt.total_seconds()

        # 2. Duplicate Detection
        dup_mask = timestamps.duplicated(keep="first")
        duplicate_count = int(dup_mask.sum())
        if duplicate_count > 0:
            logger.warning(f"Detected {duplicate_count} duplicate timestamps. Dropping redundant records.")
            df_clean = df_clean[~dup_mask].reset_index(drop=True)
            timestamps = pd.to_datetime(df_clean["timestamp"], utc=True)
            time_diffs = timestamps.diff().dt.total_seconds()

        # 3. Gap Detection (Intervals exceeding threshold)
        gaps = time_diffs > self.gap_threshold_sec
        gap_count = int(gaps.sum())
        gap_durations = time_diffs[gaps]
        max_gap = float(gap_durations.max()) if gap_count > 0 else 0.0
        total_gap = float(gap_durations.sum()) if gap_count > 0 else 0.0

        # 4. Availability Masks (Distinguish missing from measured zero!)
        solexs_flux = df_clean.get("solexs_flux", pd.Series(np.nan, index=df_clean.index))
        helios_flux = df_clean.get("helios_flux", pd.Series(np.nan, index=df_clean.index))

        solexs_valid = pd.notna(solexs_flux) & (solexs_flux >= 0.0)
        helios_valid = pd.notna(helios_flux) & (helios_flux >= 0.0)

        df_clean["solexs_valid"] = solexs_valid.astype(int)
        df_clean["helios_valid"] = helios_valid.astype(int)
        df_clean["joint_valid"] = (solexs_valid & helios_valid).astype(int)

        solexs_missing_count = int((~solexs_valid).sum())
        helios_missing_count = int((~helios_valid).sum())

        total_rec = len(df_clean)
        solexs_avail_pct = round(float(solexs_valid.mean()) * 100.0, 2)
        helios_avail_pct = round(float(helios_valid.mean()) * 100.0, 2)
        joint_avail_pct = round(float((solexs_valid & helios_valid).mean()) * 100.0, 2)

        # 5. Ratio Denominator Safeguard (Never divide by zero or below noise floor)
        div_zero_count = 0
        if "solexs_flux" in df_clean.columns and "helios_flux" in df_clean.columns:
            sxr_vals = df_clean["solexs_flux"].to_numpy(dtype=float)
            hxr_vals = df_clean["helios_flux"].to_numpy(dtype=float)

            # Mask where denominator is below physical noise threshold
            invalid_denom = (sxr_vals < self.min_denominator_threshold) | np.isnan(sxr_vals)
            div_zero_count = int(invalid_denom.sum())

            safe_hr = np.zeros_like(sxr_vals)
            valid_idx = ~invalid_denom & ~np.isnan(hxr_vals) & (hxr_vals >= 0.0)
            safe_hr[valid_idx] = hxr_vals[valid_idx] / sxr_vals[valid_idx]
            safe_hr[invalid_denom] = 0.0

            df_clean["hardness_ratio_safe"] = safe_hr

        # 6. Quality Flag Summary
        q_summary = {"NOMINAL": int((solexs_valid & helios_valid).sum()), "PARTIAL": int((solexs_valid ^ helios_valid).sum()), "DROPOUT": int((~solexs_valid & ~helios_valid).sum())}

        report = QualityAuditReport(
            total_records=total_rec,
            is_monotonic=is_monotonic,
            duplicate_count=duplicate_count,
            gap_count=gap_count,
            max_gap_duration_sec=max_gap,
            total_gap_duration_sec=total_gap,
            solexs_missing_count=solexs_missing_count,
            helios_missing_count=helios_missing_count,
            solexs_availability_pct=solexs_avail_pct,
            helios_availability_pct=helios_avail_pct,
            joint_availability_pct=joint_avail_pct,
            ratio_division_by_zero_prevented=div_zero_count,
            quality_flag_summary=q_summary,
        )

        return df_clean, report
