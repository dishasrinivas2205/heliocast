"""
Unit tests for the SpaceWeatherAlertStateMachine and probability calibration.
"""

import unittest
import numpy as np
from heliocast.alerts.state_machine import AlertLevel, SpaceWeatherAlertStateMachine


class TestAlertStateMachine(unittest.TestCase):
    """Test suite for alert transitions and calibration."""

    def test_state_transitions_and_hysteresis(self):
        """Test NOMINAL -> WATCH -> WARNING -> CRITICAL -> COOLDOWN -> NOMINAL."""
        sm = SpaceWeatherAlertStateMachine(
            watch_threshold=0.35,
            warning_threshold=0.60,
            critical_threshold=0.80,
            cooldown_steps=2,
            min_persistence_steps=1,
        )

        self.assertEqual(sm.current_state, AlertLevel.NOMINAL)

        # Watch level
        s, tr = sm.step("2024-05-14T08:00:00Z", 0.40)
        self.assertEqual(s, AlertLevel.WATCH)
        self.assertIsNotNone(tr)

        # Warning level
        s, tr = sm.step("2024-05-14T08:00:10Z", 0.65)
        self.assertEqual(s, AlertLevel.WARNING)

        # Critical level
        s, tr = sm.step("2024-05-14T08:00:20Z", 0.85)
        self.assertEqual(s, AlertLevel.CRITICAL)

        # Drop back to quiet -> enters COOLDOWN
        s, tr = sm.step("2024-05-14T08:00:30Z", 0.10)
        self.assertEqual(s, AlertLevel.COOLDOWN)

        # Cooldown step 1
        s, tr = sm.step("2024-05-14T08:00:40Z", 0.10)
        self.assertEqual(s, AlertLevel.COOLDOWN)

        # Cooldown expires -> NOMINAL
        s, tr = sm.step("2024-05-14T08:00:50Z", 0.10)
        self.assertEqual(s, AlertLevel.NOMINAL)

    def test_isotonic_calibration_fitting(self):
        """Test fitting isotonic regression calibrator on validation data."""
        sm = SpaceWeatherAlertStateMachine()

        y_true = np.array([0, 0, 0, 0, 1, 1, 1, 1])
        y_prob = np.array([0.1, 0.2, 0.35, 0.4, 0.6, 0.75, 0.85, 0.9])

        sm.fit_calibrator(y_true, y_prob)
        self.assertIsNotNone(sm.calibrator)

        # Calibrated output should be monotonic
        p_cal_low = sm.calibrate(0.15)
        p_cal_high = sm.calibrate(0.80)
        self.assertLessEqual(p_cal_low, p_cal_high)
        self.assertGreaterEqual(p_cal_low, 0.0)
        self.assertLessEqual(p_cal_high, 1.0)


if __name__ == "__main__":
    unittest.main()
