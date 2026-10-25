"""
Unit tests for chronological embargo splitting and leakage prevention.
Verifies that train, validation, and test partitions have zero overlap,
maintain non-negative embargo time buffers, and prevent future leakage.
"""

import unittest
import pandas as pd
from heliocast.forecaster.splits import make_chronological_embargo_split, verify_temporal_integrity


class TestChronologicalSplits(unittest.TestCase):
    """Test suite for leakage prevention."""

    def test_embargo_split_integrity(self):
        """Test that embargo buffer separates partitions chronologically."""
        times = pd.date_range("2024-05-14 00:00:00", periods=720, freq="10s", tz="UTC")
        df = pd.DataFrame({
            "timestamp": times,
            "solexs_flux": range(720),
            "helios_flux": range(720),
        })

        split = make_chronological_embargo_split(
            df,
            train_ratio=0.60,
            val_ratio=0.20,
            test_ratio=0.20,
            embargo_minutes=15.0,
            cadence_sec=10.0,
        )

        verification = verify_temporal_integrity(split)
        self.assertFalse(verification["has_leakage"])
        self.assertGreater(verification["train_to_val_embargo_sec"], 0)
        self.assertGreater(verification["val_to_test_embargo_sec"], 0)

        # Max timestamp in train must strictly precede min timestamp in val
        t_train_max = pd.to_datetime(split.train_df["timestamp"], utc=True).max()
        t_val_min = pd.to_datetime(split.val_df["timestamp"], utc=True).min()
        t_val_max = pd.to_datetime(split.val_df["timestamp"], utc=True).max()
        t_test_min = pd.to_datetime(split.test_df["timestamp"], utc=True).min()

        self.assertLess(t_train_max, t_val_min)
        self.assertLess(t_val_max, t_test_min)


if __name__ == "__main__":
    unittest.main()
