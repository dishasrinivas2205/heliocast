"""
End-to-End System Integration Test for HelioCast-L1.
"""

from pathlib import Path
import tempfile
import unittest

from heliocast.cli import run_pipeline


class TestE2EPipeline(unittest.TestCase):
    def test_end_to_end_pipeline_execution(self):
        # Run pipeline for 2 hours
        try:
            run_pipeline(hours=2.0, cadence=10.0)
            success = True
        except Exception as e:
            success = False
            self.fail(f"Pipeline crashed with error: {e}")

        self.assertTrue(success)


if __name__ == "__main__":
    unittest.main()
