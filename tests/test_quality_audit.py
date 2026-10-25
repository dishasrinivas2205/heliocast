"""
Unit tests for TelemetryQualityAuditor.
Verifies monotonicity detection, duplicate dropping, gap identification,
availability masking, and denominator division-by-zero protection.
"""

import unittest
import numpy as np
import pandas as pd
from heliocast.quality.audit import TelemetryQualityAuditor


class TestTelemetryQualityAudit(unittest.TestCase):
    """Test suite for data quality validation."""

    def test_clean_telemetry_audit(self):
        """Test auditing clean monotonic telemetry."""
        times = pd.date_range("2024-05-14 08:00:00", periods=60, freq="10s", tz="UTC")
        df = pd.DataFrame({
            "timestamp": times,
            "solexs_flux": np.linspace(150, 200, 60),
            "helios_flux": np.linspace(20, 50, 60),
        })

        auditor = TelemetryQualityAuditor(nominal_cadence_sec=10.0)
        df_clean, report = auditor.audit(df)

        self.assertTrue(report.is_monotonic)
        self.assertEqual(report.duplicate_count, 0)
        self.assertEqual(report.gap_count, 0)
        self.assertEqual(report.solexs_availability_pct, 100.0)
        self.assertEqual(report.helios_availability_pct, 100.0)
        self.assertIn("hardness_ratio_safe", df_clean.columns)

    def test_duplicate_and_disorder_handling(self):
        """Test that out-of-order records and duplicates are resolved correctly."""
        times = [
            "2024-05-14 08:00:20+00:00",
            "2024-05-14 08:00:10+00:00",
            "2024-05-14 08:00:10+00:00",  # Duplicate!
            "2024-05-14 08:00:30+00:00",
        ]
        df = pd.DataFrame({
            "timestamp": times,
            "solexs_flux": [150.0, 160.0, 160.0, 170.0],
            "helios_flux": [20.0, 25.0, 25.0, 30.0],
        })

        auditor = TelemetryQualityAuditor(nominal_cadence_sec=10.0)
        df_clean, report = auditor.audit(df)

        self.assertFalse(report.is_monotonic)  # Original was not monotonic
        self.assertEqual(report.duplicate_count, 1)
        self.assertEqual(len(df_clean), 3)
        # Verify cleaned dataframe is strictly monotonic
        diffs = pd.to_datetime(df_clean["timestamp"]).diff().dt.total_seconds()
        self.assertTrue((diffs.iloc[1:] > 0).all())

    def test_denominator_zero_protection(self):
        """Test that division by zero or sub-noise flux is safely guarded."""
        times = pd.date_range("2024-05-14 08:00:00", periods=5, freq="10s", tz="UTC")
        df = pd.DataFrame({
            "timestamp": times,
            "solexs_flux": [100.0, 0.0, -5.0, np.nan, 50.0],  # 0, negative, and NaN!
            "helios_flux": [20.0, 10.0, 10.0, 10.0, 10.0],
        })

        auditor = TelemetryQualityAuditor(nominal_cadence_sec=10.0, min_denominator_threshold=5.0)
        df_clean, report = auditor.audit(df)

        self.assertIn("hardness_ratio_safe", df_clean.columns)
        hr = df_clean["hardness_ratio_safe"].to_numpy()

        self.assertAlmostEqual(hr[0], 0.2, places=2)
        self.assertEqual(hr[1], 0.0)  # Zero guarded
        self.assertEqual(hr[2], 0.0)  # Negative guarded
        self.assertEqual(hr[3], 0.0)  # NaN guarded
        self.assertGreater(report.ratio_division_by_zero_prevented, 0)


if __name__ == "__main__":
    unittest.main()
