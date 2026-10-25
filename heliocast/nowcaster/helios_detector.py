"""
Independent HEL1OS Hard X-ray (10-150 keV) Non-Thermal Burst Detection Engine.
Identifies rapid impulsive chromospheric electron precipitation bursts,
non-thermal fluence, and high-energy triggers.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from scipy.signal import find_peaks, savgol_filter

from heliocast.data.schema import QualityFlag
from heliocast.logging import get_logger

logger = get_logger("heliocast.nowcaster.helios")


@dataclass
class HeliosFlareEvent:
    """Independent detection record from HEL1OS hard X-rays."""
    event_id: str
    instrument: str = "HEL1OS"
    start_time: str = ""
    peak_time: str = ""
    end_time: str = ""
    duration_seconds: float = 0.0
    peak_count_rate: float = 0.0    # count/s
    baseline_count_rate: float = 0.0 # count/s
    non_thermal_fluence: float = 0.0 # integrated count
    snr: float = 0.0
    quality_mask: int = 0


class HeliosBurstDetector:
    """
    Algorithmic detector for non-thermal Hard X-ray bursts observed by Aditya-L1 HEL1OS.
    """

    def __init__(
        self,
        baseline_window_steps: int = 90,
        snr_multiplier: float = 3.5,
        min_prominence: float = 12.0,
    ):
        self.baseline_window_steps = baseline_window_steps
        self.snr_multiplier = snr_multiplier
        self.min_prominence = min_prominence

    def detect(self, df: pd.DataFrame) -> List[HeliosFlareEvent]:
        """
        Execute independent HEL1OS impulsive burst detection on time-series telemetry.
        """
        if len(df) < 30:
            return []

        flux = df["helios_flux"].to_numpy(dtype=float)
        timestamps = pd.to_datetime(df["timestamp"]).to_numpy()
        qualities = df.get("helios_quality", pd.Series(np.zeros(len(df), dtype=int))).to_numpy()

        # Step 1: Light smoothing to preserve fast impulsive spikes (~20-100s)
        w_len = min(7, len(flux) if len(flux) % 2 != 0 else len(flux) - 1)
        smooth_flux = savgol_filter(flux, window_length=w_len, polyorder=2)

        # Step 2: Background noise estimation
        helios_base = float(np.percentile(flux, 20))
        helios_mad = float(np.median(np.abs(flux - np.median(flux))))
        sigma_est = max(helios_mad * 1.4826, 2.0)
        detection_threshold = helios_base + self.snr_multiplier * sigma_est

        # Step 3: Peak finding for fast non-thermal bursts
        peaks, _ = find_peaks(
            smooth_flux,
            height=detection_threshold,
            prominence=self.min_prominence,
            distance=15,  # ~2.5 minutes separation
        )

        detected_events = []

        for p_idx in peaks:
            peak_val = float(flux[p_idx])
            peak_dt = pd.to_datetime(timestamps[p_idx]).to_pydatetime()

            # Find burst start: where impulsive rise begins
            start_idx = max(0, p_idx - 1)
            while start_idx > 0 and smooth_flux[start_idx] > helios_base + sigma_est:
                start_idx -= 1
            start_dt = pd.to_datetime(timestamps[start_idx]).to_pydatetime()

            # Find burst end: return to background
            end_idx = min(len(flux) - 1, p_idx + 1)
            while end_idx < len(flux) - 1 and smooth_flux[end_idx] > helios_base + sigma_est:
                end_idx += 1
            end_dt = pd.to_datetime(timestamps[end_idx]).to_pydatetime()

            duration_sec = round((end_dt - start_dt).total_seconds(), 1)
            # Integrated non-thermal fluence above baseline (counts)
            burst_slice = flux[start_idx : end_idx + 1]
            fluence = float(np.sum(np.maximum(0.0, burst_slice - helios_base)))
            snr = round((peak_val - helios_base) / sigma_est, 2)
            event_id = f"HX-{peak_dt.strftime('%Y%m%d-%H%M%S')}"

            evt_qual = int(np.bitwise_or.reduce(qualities[start_idx : end_idx + 1]))

            event = HeliosFlareEvent(
                event_id=event_id,
                instrument="HEL1OS",
                start_time=start_dt.strftime("%Y-%m-%d %H:%M:%S"),
                peak_time=peak_dt.strftime("%Y-%m-%d %H:%M:%S"),
                end_time=end_dt.strftime("%Y-%m-%d %H:%M:%S"),
                duration_seconds=duration_sec,
                peak_count_rate=round(peak_val, 2),
                baseline_count_rate=round(helios_base, 2),
                non_thermal_fluence=round(fluence, 2),
                snr=snr,
                quality_mask=evt_qual,
            )
            detected_events.append(event)

        logger.info(f"Independent HEL1OS detector identified {len(detected_events)} non-thermal bursts.")
        return detected_events
