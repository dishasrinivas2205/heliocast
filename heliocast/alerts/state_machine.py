"""
Operational Space Weather Alert State Machine & Probability Calibration.
Implements hysteresis, deduplication, cooldown windows, and probability calibration
(Isotonic Regression) strictly fitted on validation partitions.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from sklearn.isotonic import IsotonicRegression

from heliocast.logging import get_logger

logger = get_logger("heliocast.alerts.state_machine")


class AlertLevel(str, Enum):
    NOMINAL = "NOMINAL"
    WATCH = "WATCH"           # P >= 0.35
    WARNING = "WARNING"       # P >= 0.60
    CRITICAL = "CRITICAL"     # P >= 0.80
    COOLDOWN = "COOLDOWN"     # Recovery phase post-flare


@dataclass
class AlertTransitionRecord:
    """Audit record for space weather alert state transitions."""
    transition_id: str
    timestamp: str
    previous_state: str
    new_state: str
    calibrated_probability: float
    trigger_reason: str
    event_id: Optional[str] = None


class SpaceWeatherAlertStateMachine:
    """
    Finite state machine regulating operational flare alerts.
    Enforces hysteresis, minimum persistence, and post-event cooldown.
    """

    def __init__(
        self,
        watch_threshold: float = 0.35,
        warning_threshold: float = 0.60,
        critical_threshold: float = 0.80,
        cooldown_steps: int = 90,           # ~15 min at 10s cadence
        min_persistence_steps: int = 2,      # Require 2 consecutive frames to escalate
    ):
        self.watch_threshold = watch_threshold
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.cooldown_steps = cooldown_steps
        self.min_persistence_steps = min_persistence_steps

        self.current_state = AlertLevel.NOMINAL
        self.consecutive_high_frames = 0
        self.cooldown_counter = 0
        self.history: List[AlertTransitionRecord] = []
        self.calibrator: Optional[IsotonicRegression] = None

    def fit_calibrator(self, y_val_true: np.ndarray, y_val_prob: np.ndarray) -> None:
        """
        Fit isotonic probability calibration on independent validation set.
        Never fit on test data!
        """
        self.calibrator = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        self.calibrator.fit(y_val_prob, y_val_true)
        logger.info("Fitted Isotonic probability calibrator on validation partition.")

    def calibrate(self, raw_prob: float) -> float:
        """Calibrate a single probability estimate."""
        if self.calibrator is None:
            return float(np.clip(raw_prob, 0.0, 1.0))
        return float(self.calibrator.predict([raw_prob])[0])

    def step(
        self,
        timestamp: str,
        raw_prob: float,
        event_id: Optional[str] = None,
    ) -> Tuple[AlertLevel, Optional[AlertTransitionRecord]]:
        """
        Evaluate single time step and transition state machine.
        """
        p_cal = self.calibrate(raw_prob)
        prev_state = self.current_state
        new_state = prev_state
        transition = None

        # Check cooldown state
        if self.current_state == AlertLevel.COOLDOWN:
            self.cooldown_counter -= 1
            if self.cooldown_counter <= 0:
                new_state = AlertLevel.NOMINAL
                reason = "Cooldown window expired; returning to nominal baseline"
                transition = AlertTransitionRecord(
                    transition_id=f"TR-{len(self.history)+1:04d}",
                    timestamp=timestamp,
                    previous_state=prev_state.value,
                    new_state=new_state.value,
                    calibrated_probability=p_cal,
                    trigger_reason=reason,
                    event_id=event_id,
                )
            self.current_state = new_state
            if transition:
                self.history.append(transition)
            return new_state, transition

        # Persistence accumulation
        if p_cal >= self.watch_threshold:
            self.consecutive_high_frames += 1
        else:
            self.consecutive_high_frames = max(0, self.consecutive_high_frames - 1)

        # State transition logic
        if p_cal >= self.critical_threshold and self.consecutive_high_frames >= self.min_persistence_steps:
            if self.current_state != AlertLevel.CRITICAL:
                new_state = AlertLevel.CRITICAL
                reason = f"Calibrated probability {p_cal:.2f} >= critical threshold ({self.critical_threshold})"
        elif p_cal >= self.warning_threshold and self.consecutive_high_frames >= self.min_persistence_steps:
            if self.current_state not in [AlertLevel.WARNING, AlertLevel.CRITICAL]:
                new_state = AlertLevel.WARNING
                reason = f"Calibrated probability {p_cal:.2f} >= warning threshold ({self.warning_threshold})"
        elif p_cal >= self.watch_threshold:
            if self.current_state == AlertLevel.NOMINAL:
                new_state = AlertLevel.WATCH
                reason = f"Calibrated probability {p_cal:.2f} >= watch threshold ({self.watch_threshold})"
        else:
            # Dropdown with cooldown initiation if leaving warning/critical
            if self.current_state in [AlertLevel.WARNING, AlertLevel.CRITICAL]:
                new_state = AlertLevel.COOLDOWN
                self.cooldown_counter = self.cooldown_steps
                reason = "Probability subsided; entering cooldown buffer to prevent alert chatter"
            elif self.current_state == AlertLevel.WATCH and p_cal < (self.watch_threshold * 0.7):
                # Hysteresis buffer
                new_state = AlertLevel.NOMINAL
                reason = "Probability cleared watch threshold hysteresis floor"

        if new_state != prev_state and transition is None:
            transition = AlertTransitionRecord(
                transition_id=f"TR-{len(self.history)+1:04d}",
                timestamp=timestamp,
                previous_state=prev_state.value,
                new_state=new_state.value,
                calibrated_probability=p_cal,
                trigger_reason=reason,
                event_id=event_id,
            )
            self.history.append(transition)

        self.current_state = new_state
        return new_state, transition
