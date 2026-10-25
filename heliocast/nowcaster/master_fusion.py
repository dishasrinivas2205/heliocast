"""
Master Catalogue Fusion Engine for Aditya-L1 Solar Flare Nowcasting.
Fulfills Step 3 of ISRO Problem Statement 15:
Combines independent SoLEXS (Soft X-ray) and HEL1OS (Hard X-ray) catalogues
into a unified Master Flare Catalogue with rigorous physical Neupert effect verification.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from scipy.signal import savgol_filter

from heliocast.logging import get_logger
from heliocast.nowcaster.helios_detector import HeliosBurstDetector, HeliosFlareEvent
from heliocast.nowcaster.solexs_detector import SolexsFlareDetector, SolexsFlareEvent

logger = get_logger("heliocast.nowcaster.fusion")


@dataclass
class MasterFlareEvent:
    """Consolidated multi-instrument flare record."""
    master_id: str
    flare_class: str
    start_time: str
    peak_time: str
    end_time: str
    duration_minutes: float
    solexs_peak_flux: float
    helios_peak_count_rate: float
    spectral_hardness_ratio: float
    neupert_correlation: float
    neupert_verified: bool
    confirmation_status: str        # CONFIRMED_ERUPTION, THERMAL_ONLY, TRANSIENT_GLITCH
    confidence_score: float         # 0.0 to 1.0
    solexs_event_id: Optional[str] = None
    helios_event_id: Optional[str] = None
    dispatched_alert: bool = False


class MasterCatalogueFusion:
    """
    Fuses independent SoLEXS and HEL1OS detections through physical coincidence
    and Neupert correlation analysis.
    """

    def __init__(
        self,
        max_coincidence_sec: float = 180.0,
        min_neupert_correlation: float = 0.55,
    ):
        self.max_coincidence_sec = max_coincidence_sec
        self.min_neupert_correlation = min_neupert_correlation

    def fuse(
        self,
        solexs_events: List[SolexsFlareEvent],
        helios_events: List[HeliosFlareEvent],
        telemetry_df: pd.DataFrame,
    ) -> List[MasterFlareEvent]:
        """
        Merge independent detection catalogues into the Master Catalogue.
        """
        if not solexs_events:
            logger.info("No SoLEXS events to fuse.")
            return []

        # Prepare telemetry arrays for Neupert derivative correlation
        sxr_flux = telemetry_df["solexs_flux"].to_numpy(dtype=float)
        hxr_flux = telemetry_df["helios_flux"].to_numpy(dtype=float)
        ts_series = pd.to_datetime(telemetry_df["timestamp"], utc=True)

        w_len = min(15, len(sxr_flux) if len(sxr_flux) % 2 != 0 else len(sxr_flux) - 1)
        smooth_sxr = savgol_filter(sxr_flux, window_length=w_len, polyorder=2)
        d_sxr = np.gradient(smooth_sxr)
        d_sxr_pos = np.maximum(0.0, d_sxr)

        matched_helios_ids = set()
        master_records: List[MasterFlareEvent] = []

        for sx_evt in solexs_events:
            sx_peak_dt = pd.to_datetime(sx_evt.peak_time, utc=True)
            sx_start_dt = pd.to_datetime(sx_evt.start_time, utc=True)
            sx_end_dt = pd.to_datetime(sx_evt.end_time, utc=True)

            # Search for coincident HEL1OS burst during the rise phase [start, peak + max_delay]
            best_hx_match: Optional[HeliosFlareEvent] = None
            min_delay = float("inf")

            for hx_evt in helios_events:
                hx_peak_dt = pd.to_datetime(hx_evt.peak_time, utc=True)
                # The HEL1OS impulsive burst typically occurs during the rise phase of SoLEXS
                delay_from_rise = (hx_peak_dt - sx_start_dt).total_seconds()
                delay_from_peak = abs((hx_peak_dt - sx_peak_dt).total_seconds())

                if -60.0 <= delay_from_rise <= (sx_peak_dt - sx_start_dt).total_seconds() + self.max_coincidence_sec:
                    if delay_from_peak < min_delay:
                        min_delay = delay_from_peak
                        best_hx_match = hx_evt

            # Calculate Neupert correlation: corr(dF_SXR/dt, F_HXR) during rise phase
            mask_rise = (ts_series >= sx_start_dt) & (ts_series <= sx_peak_dt)
            rise_indices = np.where(mask_rise.to_numpy())[0]

            neupert_r = 0.0
            if len(rise_indices) >= 4:
                sub_dsxr = d_sxr_pos[rise_indices]
                sub_hxr = hxr_flux[rise_indices]
                if np.std(sub_dsxr) > 1e-4 and np.std(sub_hxr) > 1e-4:
                    r_mat = np.corrcoef(sub_dsxr, sub_hxr)
                    neupert_r = float(r_mat[0, 1])
                    if np.isnan(neupert_r):
                        neupert_r = 0.0

            # Evaluate Neupert Verification status
            neupert_verified = bool(
                best_hx_match is not None
                and (neupert_r >= self.min_neupert_correlation or best_hx_match.snr >= 5.0)
            )

            # Calculate joint spectral hardness ratio
            hxr_peak = best_hx_match.peak_count_rate if best_hx_match else float(np.mean(hxr_flux[rise_indices])) if len(rise_indices) > 0 else 10.0
            hardness = float(hxr_peak / max(sx_evt.peak_flux, 1e-3))

            # Determine Confirmation Status & Confidence
            if neupert_verified:
                status = "CONFIRMED_ERUPTION"
                confidence = min(0.99, max(0.85, 0.70 + 0.20 * neupert_r + 0.05 * min(sx_evt.snr / 10.0, 1.0)))
            elif best_hx_match is not None:
                status = "MULTI_BAND_UNVERIFIED"
                confidence = 0.70
            elif sx_evt.snr > 15.0 and sx_evt.duration_minutes > 10.0:
                status = "THERMAL_GRADUAL_FLARE"
                confidence = 0.78
            else:
                status = "SUSPECT_GLITCH"
                confidence = 0.40

            master_id = f"AL1-{sx_peak_dt.strftime('%Y%m%d-%H%M%S')}"
            if best_hx_match:
                matched_helios_ids.add(best_hx_match.event_id)

            master_evt = MasterFlareEvent(
                master_id=master_id,
                flare_class=sx_evt.flare_class,
                start_time=sx_evt.start_time,
                peak_time=sx_evt.peak_time,
                end_time=sx_evt.end_time,
                duration_minutes=sx_evt.duration_minutes,
                solexs_peak_flux=sx_evt.peak_flux,
                helios_peak_count_rate=round(hxr_peak, 2),
                spectral_hardness_ratio=round(hardness, 4),
                neupert_correlation=round(neupert_r, 3),
                neupert_verified=neupert_verified,
                confirmation_status=status,
                confidence_score=round(confidence, 2),
                solexs_event_id=sx_evt.event_id,
                helios_event_id=best_hx_match.event_id if best_hx_match else None,
            )
            master_records.append(master_evt)

        logger.info(
            f"Master Catalogue Fusion complete: {len(master_records)} flares catalogued "
            f"({sum(1 for m in master_records if m.neupert_verified)} Neupert verified)."
        )
        return master_records
