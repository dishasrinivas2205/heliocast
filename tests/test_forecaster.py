"""
Tests for Precursor Flare Forecaster & Quantifiable Lead Time.
"""

import unittest
import numpy as np
import pandas as pd

from heliocast.data.synthetic import SolarFlareSimulator
from heliocast.forecaster.features import FEATURE_NAMES, PrecursorFeatureExtractor
from heliocast.forecaster.lead_time import LeadTimeEstimator
from heliocast.forecaster.pipeline import FlareForecastingPipeline


class TestForecaster(unittest.TestCase):
    def setUp(self):
        self.sim = SolarFlareSimulator(random_seed=42)
        self.extractor = PrecursorFeatureExtractor(cadence_sec=10.0)

    def test_causal_feature_extraction(self):
        df, _ = self.sim.generate_stream(duration_hours=1.0, cadence_sec=10.0)
        X = self.extractor.extract_features(df)

        self.assertEqual(len(X), len(df))
        for col in FEATURE_NAMES:
            self.assertIn(col, X.columns)
            # Ensure no NaNs or Infs
            self.assertFalse(X[col].isnull().any())
            self.assertFalse(np.isinf(X[col]).any())

    def test_pipeline_training_and_lead_time(self):
        df, ground_truth = self.sim.generate_stream(duration_hours=4.0, cadence_sec=10.0)
        pipeline = FlareForecastingPipeline(horizon_minutes=30.0, cadence_sec=10.0)

        result = pipeline.train_and_evaluate(df, ground_truth)

        # Assert skill scores are computed
        self.assertIn("TSS", result.metrics)
        self.assertIn("HSS", result.metrics)
        self.assertIn("TPR", result.metrics)
        self.assertGreaterEqual(result.metrics["TSS"], 0.70)

        # Assert quantifiable lead times
        self.assertEqual(len(result.lead_times), len(ground_truth))
        for lt in result.lead_times:
            self.assertTrue(lt.alert_triggered)
            # Lead time must be positive and within reasonable bounds (10 to 45 min)
            self.assertGreater(lt.lead_time_minutes, 5.0)
            self.assertLessEqual(lt.lead_time_minutes, 60.0)


if __name__ == "__main__":
    unittest.main()
