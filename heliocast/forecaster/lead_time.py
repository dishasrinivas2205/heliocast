"""
Quantifiable Lead-Time & Pre-Onset Warning Evaluation Subsystem.
Strictly distinguishes genuine pre-onset advance warnings from post-onset detection delay.
Evaluates false alarms per observing hour and lead-time distributions.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from heliocast.logging import get_logger

logger = get_logger("heliocast.forecaster.lead_time")


@dataclass
class LeadTimeRecord:
    """Individual lead-time assessment for a flare event."""
    event_id: str
    flare_class: str
    onset_time: Optional[str]
    peak_time: str
    alert_trigger_time: Optional[str]
    lead_time_minutes: float                # Maintained for backwards compatibility (to peak)
    lead_time_to_onset_minutes: float       # Genuine pre-onset warning time (positive if before onset)
    detection_delay_minutes: float          # Delay if alerted after onset
    alert_triggered: bool
    is_pre_onset: bool                      # True only if alert was issued BEFORE onset
    status: str                             # GENUINE_ADVANCE_WARNING, POST_ONSET_DETECTION, MISSED_EVENT


class LeadTimeEstimator:
    """
    Computes rigorous empirical lead times and false alarms per observing hour.
    """

    def __init__(
        self,
        alert_threshold: float = 0.60,
        max_lookahead_min: float = 60.0,
        min_lead_min: float = 5.0,
    ):
        self.alert_threshold = alert_threshold
        self.max_lookahead_min = max_lookahead_min
        self.min_lead_min = min_lead_min

    def evaluate(
        self,
        telemetry_df: pd.DataFrame,
        probabilities: np.ndarray,
        flare_events: List[Dict[str, Any]],
    ) -> List[LeadTimeRecord]:
        """
        Compute pre-onset warning times and detection delays for each solar flare event.
        """
        timestamps = pd.to_datetime(telemetry_df["timestamp"], utc=True)
        results: List[LeadTimeRecord] = []

        for fl in flare_events:
            peak_dt = pd.to_datetime(fl.get("peak_time"), utc=True)
            # Default onset ~15 min prior to peak if unrecorded
            onset_val = fl.get("start_time") or fl.get("onset_time")
            onset_dt = pd.to_datetime(onset_val, utc=True) if onset_val else peak_dt - pd.Timedelta(minutes=15.0)

            fl_class = fl.get("flare_class", "C1.0")
            event_id = fl.get("event_id", f"AL1-{peak_dt.strftime('%Y%m%d-%H%M%S')}")

            # Precursor evaluation window: up to max_lookahead prior to peak
            precursor_mask = (
                (timestamps >= peak_dt - pd.Timedelta(minutes=self.max_lookahead_min))
                & (timestamps <= peak_dt)
            )
            prec_indices = np.where(precursor_mask.to_numpy())[0]

            alert_time = None
            lead_time_peak_min = 0.0
            lead_time_onset_min = 0.0
            detection_delay_min = 0.0
            alert_triggered = False
            is_pre_onset = False

            if len(prec_indices) > 0:
                prob_slice = probabilities[prec_indices]
                trigger_locs = np.where(prob_slice >= self.alert_threshold)[0]

                if len(trigger_locs) > 0:
                    earliest_idx = prec_indices[trigger_locs[0]]
                    alert_time = timestamps.iloc[earliest_idx]
                    alert_triggered = True

                    # Calculate lead times
                    lead_time_peak_min = round((peak_dt - alert_time).total_seconds() / 60.0, 1)

                    if alert_time < onset_dt:
                        is_pre_onset = True
                        lead_time_onset_min = round((onset_dt - alert_time).total_seconds() / 60.0, 1)
                    else:
                        detection_delay_min = round((alert_time - onset_dt).total_seconds() / 60.0, 1)

            if is_pre_onset and lead_time_onset_min >= self.min_lead_min:
                status = "GENUINE_ADVANCE_WARNING"
            elif alert_triggered and is_pre_onset:
                status = "MARGINAL_WARNING"
            elif alert_triggered:
                status = "POST_ONSET_DETECTION"
            else:
                status = "MISSED_EVENT"

            results.append(
                LeadTimeRecord(
                    event_id=event_id,
                    flare_class=fl_class,
                    onset_time=onset_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    peak_time=peak_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    alert_trigger_time=alert_time.strftime("%Y-%m-%d %H:%M:%S") if alert_time else None,
                    lead_time_minutes=lead_time_peak_min,
                    lead_time_to_onset_minutes=lead_time_onset_min,
                    detection_delay_minutes=detection_delay_min,
                    alert_triggered=alert_triggered,
                    is_pre_onset=is_pre_onset,
                    status=status,
                )
            )

        return results

    @staticmethod
    def calculate_false_alarm_burden(
        telemetry_df: pd.DataFrame,
        probabilities: np.ndarray,
        flare_events: List[Dict[str, Any]],
        alert_threshold: float = 0.60,
        cadence_sec: float = 10.0,
    ) -> Dict[str, float]:
        """
        Calculate false alarms per observing hour over non-event intervals.
        """
        timestamps = pd.to_datetime(telemetry_df["timestamp"], utc=True)
        total_hours = len(telemetry_df) * cadence_sec / 3600.0

        # Create event mask
        event_mask = np.zeros(len(telemetry_df), dtype=bool)
        for fl in flare_events:
            peak_dt = pd.to_datetime(fl.get("peak_time"), utc=True)
            onset_dt = pd.to_datetime(fl.get("start_time") or fl.get("onset_time"), utc=True) if fl.get("start_time") else peak_dt - pd.Timedelta(minutes=30.0)
            end_dt = pd.to_datetime(fl.get("end_time"), utc=True) if fl.get("end_time") else peak_dt + pd.Timedelta(minutes=45.0)

            in_event = (timestamps >= onset_dt - pd.Timedelta(minutes=30.0)) & (timestamps <= end_dt)
            event_mask |= in_event.to_numpy()

        quiet_mask = ~event_mask
        quiet_hours = quiet_mask.sum() * cadence_sec / 3600.0

        # Unmatched alerts in quiet periods
        quiet_alerts = (probabilities[quiet_mask] >= alert_threshold).sum()
        rate_per_hour = round(float(quiet_alerts / max(0.1, quiet_hours)), 3)

        return {
            "total_observing_hours": round(total_hours, 2),
            "quiet_observing_hours": round(quiet_hours, 2),
            "false_alarms_in_quiet": int(quiet_alerts),
            "false_alarms_per_hour": rate_per_hour,
        }
