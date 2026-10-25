"""
Tests for Physics-Based Aditya-L1 Telemetry Simulator.
"""

import unittest
import numpy as np
import pandas as pd

from heliocast.data.synthetic import SolarFlareSimulator


class TestSyntheticSimulator(unittest.TestCase):
    def setUp(self):
        self.sim = SolarFlareSimulator(random_seed=42)

    def test_generate_stream_structure(self):
        df, events = self.sim.generate_stream(duration_hours=2.0, cadence_sec=10.0)
        self.assertEqual(len(df), 720)
        self.assertIn("timestamp", df.columns)
        self.assertIn("solexs_flux", df.columns)
        self.assertIn("helios_flux", df.columns)
        self.assertIn("hardness_ratio", df.columns)
        self.assertIn("flare_active", df.columns)
        self.assertGreater(len(events), 0)

    def test_neupert_physics_correlation(self):
        # Generate flare event with strong Neupert coupling
        custom_flare = [{
            "class": "M",
            "magnitude": 5.0,
            "peak_step": 360,
            "rise_min": 15.0,
            "decay_min": 30.0,
            "neupert_coupling": 0.95,
        }]
        df, _ = self.sim.generate_stream(duration_hours=2.0, cadence_sec=10.0, flare_events=custom_flare)

        # In impulsive phase, HEL1OS flux should correlate with positive derivative of SoLEXS
        sxr = df["solexs_flux"].to_numpy()
        hxr = df["helios_flux"].to_numpy()
        d_sxr = np.maximum(0.0, np.gradient(sxr))

        # Check peak alignment: HXR peak occurs around the maximum rate of change of SXR
        max_rate_step = np.argmax(d_sxr[200:400]) + 200
        max_hxr_step = np.argmax(hxr[200:400]) + 200

        # Impulsive phase alignment within 1 minute (6 steps)
        self.assertLessEqual(abs(max_rate_step - max_hxr_step), 6)


if __name__ == "__main__":
    unittest.main()
