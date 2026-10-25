"""
Unit tests for data ingestion manifest and checksum verification.
"""

import tempfile
import unittest
from pathlib import Path
from heliocast.data.manifest import IngestionManifest


class TestIngestionManifest(unittest.TestCase):
    """Test suite for manifest provenance."""

    def test_checksum_and_registration(self):
        """Test SHA-256 calculation and manifest registration."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            manifest_file = tmp_path / "manifest.json"
            sample_data = tmp_path / "test_data.csv"

            # Create sample CSV
            sample_data.write_text("timestamp,solexs_flux,helios_flux\n2024-05-14T08:00:00Z,150.0,20.0\n")

            manifest = IngestionManifest(manifest_path=manifest_file)
            record = manifest.inspect_and_register_file(sample_data)

            self.assertTrue(record.is_valid)
            self.assertEqual(len(record.sha256_checksum), 64)
            self.assertEqual(record.file_name, "test_data.csv")
            self.assertEqual(record.frame_count, 1)

            # Reload manifest and verify persistence
            manifest2 = IngestionManifest(manifest_path=manifest_file)
            self.assertIn(record.sha256_checksum, manifest2.records)


if __name__ == "__main__":
    unittest.main()
