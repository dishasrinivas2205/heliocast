"""
Independent SoLEXS Soft X-ray (1-22 keV) Flare Detection Engine.
Performs noise-aware thresholding, flare boundary segmentation,
and standard solar flare classification (A, B, C, M, X).
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from scipy.signal import find_peaks, savgol_filter

from heliocast.data.schema import QualityFlag
from heliocast.logging import get_logger

logger = get_logger("heliocast.nowcaster.solexs")


@dataclass
class SolexsFlareEvent:
    """Independent detection record from SoLEXS soft X-rays."""
    event_id: str
    instrument: str = "SOLEXS"
    start_time: str = ""
    peak_time: str = ""
    end_time: str = ""
    duration_minutes: float = 0.0
    peak_flux: float = 0.0          # count/s
    baseline_flux: float = 0.0      # count/s
    net_flare_flux: float = 0.0     # peak - baseline
    flare_class: str = "B1.0"
    quality_mask: int = 0
    snr: float = 0.0


class SolexsFlareDetector:
    """
    Algorithmic detector for Soft X-ray flares observed by Aditya-L1 SoLEXS.
    """

    def __init__(
        self,
        baseline_window_steps: int = 90,    # ~15 min at 10s cadence
        snr_multiplier: float = 4.0,        # 4-sigma above MAD
        min_prominence: float = 30.0,       # Minimum count rate prominence
    ):
        self.baseline_window_steps = baseline_window_steps
        self.snr_multiplier = snr_multiplier
        self.min_prominence = min_prominence

    @staticmethod
    def classify_flare(peak_flux: float) -> str:
        """
        Calibrated classification mapping SoLEXS Silicon Drift Detector count rates
        to standard GOES-equivalent solar flare classes (A, B, C, M, X).
        """
        if peak_flux < 50.0:
            val = max(1.0, round(peak_flux / 5.0, 1))
            return f"A{val}"
        elif peak_flux < 300.0:
            val = max(1.0, round(peak_flux / 30.0, 1))
            return f"B{val}"
        elif peak_flux < 3000.0:
            val = max(1.0, round(peak_flux / 300.0, 1))
            return f"C{val}"
        elif peak_flux < 25000.0:
            val = max(1.0, round(peak_flux / 2500.0, 1))
            return f"M{val}"
        else:
            val = max(1.0, round(peak_flux / 25000.0, 1))
            return f"X{val}"

    def detect(self, df: pd.DataFrame) -> List[SolexsFlareEvent]:
        """
        Execute independent SoLEXS flare detection on time-series telemetry.
        """
        if len(df) < 30:
            return []

        flux = df["solexs_flux"].to_numpy(dtype=float)
        timestamps = pd.to_datetime(df["timestamp"]).to_numpy()
        qualities = df.get("solexs_quality", pd.Series(np.zeros(len(df), dtype=int))).to_numpy()

        # Step 1: Noise suppression via Savitzky-Golay filtering
        w_len = min(15, len(flux) if len(flux) % 2 != 0 else len(flux) - 1)
        smooth_flux = savgol_filter(flux, window_length=w_len, polyorder=2)
        d_flux = np.gradient(smooth_flux)

        # Step 2: Robust quiet-Sun baseline & Median Absolute Deviation (MAD)
        solexs_base = float(np.percentile(flux, 20))
        solexs_mad = float(np.median(np.abs(flux - np.median(flux))))
        sigma_est = max(solexs_mad * 1.4826, 4.0)
        detection_threshold = solexs_base + self.snr_multiplier * sigma_est

        # Step 3: Peak identification
        peaks, props = find_peaks(
            smooth_flux,
            height=detection_threshold,
            prominence=self.min_prominence,
            distance=25,  # ~4.2 minutes separation minimum
        )

        detected_events = []

        for p_idx in peaks:
            peak_val = float(flux[p_idx])
            peak_dt = pd.to_datetime(timestamps[p_idx]).to_pydatetime()

            # Backtrack to find flare start: where flux rises above baseline + 1 sigma
            start_idx = max(0, p_idx - 1)
            while start_idx > 0 and (smooth_flux[start_idx] > solexs_base + sigma_est or d_flux[start_idx] > 0.4):
                start_idx -= 1
            start_dt = pd.to_datetime(timestamps[start_idx]).to_pydatetime()

            # Forward-track to find flare end: recovery to 50% of flare peak above baseline (NOAA standard)
            end_idx = min(len(flux) - 1, p_idx + 1)
            recovery_target = solexs_base + 0.50 * (peak_val - solexs_base)
            while end_idx < len(flux) - 1 and smooth_flux[end_idx] > recovery_target:
                end_idx += 1
            end_dt = pd.to_datetime(timestamps[end_idx]).to_pydatetime()

            duration_min = round((end_dt - start_dt).total_seconds() / 60.0, 2)
            flare_cls = self.classify_flare(peak_val)
            snr = round((peak_val - solexs_base) / sigma_est, 2)
            event_id = f"SX-{peak_dt.strftime('%Y%m%d-%H%M%S')}"

            # Aggregate quality flags during event
            evt_qual = int(np.bitwise_or.reduce(qualities[start_idx : end_idx + 1]))

            event = SolexsFlareEvent(
                event_id=event_id,
                instrument="SOLEXS",
                start_time=start_dt.strftime("%Y-%m-%d %H:%M:%S"),
                peak_time=peak_dt.strftime("%Y-%m-%d %H:%M:%S"),
                end_time=end_dt.strftime("%Y-%m-%d %H:%M:%S"),
                duration_minutes=duration_min,
                peak_flux=round(peak_val, 2),
                baseline_flux=round(solexs_base, 2),
                net_flare_flux=round(peak_val - solexs_base, 2),
                flare_class=flare_cls,
                quality_mask=evt_qual,
                snr=snr,
            )
            detected_events.append(event)

        logger.info(f"Independent SoLEXS detector identified {len(detected_events)} flare events.")
        return detected_events
