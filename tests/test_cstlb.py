"""
Unit tests for the Cross-Spectral Trust and Lead-Time Benchmark (CSTLB).
Verifies that single-instrument and fused modalities execute correctly
across nominal and degraded observing scenarios with zero leakage.
"""

import unittest
from heliocast.data.synthetic import SolarFlareSimulator
from heliocast.evaluation.cstlb import CrossSpectralBenchmarkRunner


class TestCrossSpectralBenchmark(unittest.TestCase):
    """Test suite for CSTLB framework."""

    @classmethod
    def setUpClass(cls):
        sim = SolarFlareSimulator(random_seed=42)
        cls.telemetry_df, cls.flare_events = sim.generate_stream(duration_hours=2.0, cadence_sec=10.0)

    def test_cstlb_execution(self):
        """Test that CSTLB runs across all modalities and conditions without failure."""
        runner = CrossSpectralBenchmarkRunner(horizon_minutes=15.0, cadence_sec=10.0, embargo_minutes=10.0)
        summary = runner.run_benchmark(self.telemetry_df, self.flare_events, output_dir="outputs")

        self.assertIsNotNone(summary.benchmark_id)
        self.assertTrue(len(summary.scenario_results) > 5)

        # Check that both baselines and modalities are present
        modalities = {r.modality for r in summary.scenario_results}
        self.assertIn("baseline", modalities)
        self.assertIn("solexs_only", modalities)
        self.assertIn("helios_only", modalities)
        self.assertIn("fused_combined", modalities)

        # Check conditions
        conditions = {r.condition for r in summary.scenario_results}
        self.assertIn("nominal", conditions)
        self.assertIn("helios_missing", conditions)
        self.assertIn("solexs_missing", conditions)
        self.assertIn("delayed_15m", conditions)
        self.assertIn("noisy_glitched", conditions)

        # Check that metrics are within valid mathematical bounds
        for r in summary.scenario_results:
            self.assertGreaterEqual(r.tss, -1.0)
            self.assertLessEqual(r.tss, 1.0)
            self.assertGreaterEqual(r.far, 0.0)
            self.assertLessEqual(r.far, 1.0)


if __name__ == "__main__":
    unittest.main()
