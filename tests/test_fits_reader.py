"""
Tests for ISSDC PRADAN Level-1 FITS Reader & Exporter.
"""

from pathlib import Path
import tempfile
import unittest
import numpy as np
import pandas as pd

from heliocast.data.fits_reader import AdityaFitsReader
from heliocast.data.synthetic import SolarFlareSimulator


class TestFitsReader(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.reader = AdityaFitsReader()
        self.sim = SolarFlareSimulator(random_seed=42)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_write_and_read_fits(self):
        df, _ = self.sim.generate_stream(duration_hours=1.0, cadence_sec=10.0)
        fits_file = Path(self.temp_dir.name) / "test_solexs.fits"

        # Write FITS
        self.reader.write_fits_lightcurve(df, fits_file, instrument="SOLEXS")
        self.assertTrue(fits_file.exists())

        # Inspect Header
        info = self.reader.inspect_file(fits_file)
        self.assertEqual(info["telescope"], "ADITYA-L1")
        self.assertEqual(info["instrument"], "SOLEXS")

        # Read back table
        df_read = self.reader.read_lightcurve(fits_file)
        self.assertEqual(len(df_read), len(df))
        self.assertIn("timestamp", df_read.columns)
        self.assertIn("flux", df_read.columns)

    def test_synchronize_observations(self):
        df, _ = self.sim.generate_stream(duration_hours=1.0, cadence_sec=10.0)
        solexs_file = Path(self.temp_dir.name) / "sxr.fits"
        helios_file = Path(self.temp_dir.name) / "hxr.fits"

        self.reader.write_fits_lightcurve(df, solexs_file, instrument="SOLEXS")
        self.reader.write_fits_lightcurve(df, helios_file, instrument="HEL1OS")

        synced = self.reader.synchronize_observations(solexs_file, helios_file, cadence_sec=10.0)
        self.assertIn("solexs_flux", synced.columns)
        self.assertIn("helios_flux", synced.columns)
        self.assertIn("hardness_ratio", synced.columns)
        self.assertGreater(len(synced), 0)


if __name__ == "__main__":
    unittest.main()
