"""
Tests for Algorithmic Nowcaster & Master Catalogue Fusion.
"""

from pathlib import Path
import tempfile
import unittest
import numpy as np
import pandas as pd

from heliocast.data.synthetic import SolarFlareSimulator
from heliocast.nowcaster import (
    FlareCatalogDatabase,
    HeliosBurstDetector,
    MasterCatalogueFusion,
    SolarFlareNowcaster,
    SolexsFlareDetector,
)


class TestNowcaster(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "test_flares.db")
        self.nowcaster = SolarFlareNowcaster(db_path=self.db_path)
        self.sim = SolarFlareSimulator(random_seed=42)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_independent_detectors_and_fusion(self):
        df, gt = self.sim.generate_stream(duration_hours=4.0, cadence_sec=10.0)

        # 1. Independent SoLEXS detection
        sx_evts = self.nowcaster.solexs_detector.detect(df)
        self.assertGreaterEqual(len(sx_evts), 1)
        for ev in sx_evts:
            self.assertEqual(ev.instrument, "SOLEXS")
            self.assertTrue(ev.flare_class[0] in ["A", "B", "C", "M", "X"])

        # 2. Independent HEL1OS detection
        hx_evts = self.nowcaster.helios_detector.detect(df)
        self.assertGreaterEqual(len(hx_evts), 1)
        for ev in hx_evts:
            self.assertEqual(ev.instrument, "HEL1OS")
            self.assertGreater(ev.peak_count_rate, 0.0)

        # 3. Master Fusion
        master_evts = self.nowcaster.fusion.fuse(sx_evts, hx_evts, df)
        self.assertGreaterEqual(len(master_evts), 1)

        # Verify Neupert verification flag presence
        verified_count = sum(1 for m in master_evts if m.neupert_verified)
        self.assertGreaterEqual(verified_count, 1)

    def test_database_persistence_and_export(self):
        df, _ = self.sim.generate_stream(duration_hours=2.0, cadence_sec=10.0)
        sx, hx, master = self.nowcaster.process_telemetry(df)

        catalog_df = self.nowcaster.get_master_catalog()
        self.assertEqual(len(catalog_df), len(master))

        # Test CSV export
        csv_path = str(Path(self.temp_dir.name) / "master_cat.csv")
        out = self.nowcaster.db.export_csv(csv_path)
        self.assertTrue(Path(out).exists())


if __name__ == "__main__":
    unittest.main()
