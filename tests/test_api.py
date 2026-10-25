"""
Tests for FastAPI Scientific Server Routes.
"""

import unittest
from fastapi.testclient import TestClient

from heliocast.api.app import app


class TestApiServer(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_endpoint(self):
        resp = self.client.get("/api/v1/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ONLINE")
        self.assertIn("SOLEXS", data["instruments"])
        self.assertIn("HEL1OS", data["instruments"])

    def test_telemetry_latest(self):
        resp = self.client.get("/api/v1/telemetry/latest")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("solexs_flux", data)
        self.assertIn("helios_flux", data)
        self.assertIn("hardness_ratio", data)

    def test_telemetry_lightcurve(self):
        resp = self.client.get("/api/v1/telemetry/lightcurve?limit=60")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["count"], 60)
        self.assertGreaterEqual(len(data["data"]), 60)

    def test_master_catalog_endpoint(self):
        resp = self.client.get("/api/v1/catalog/master")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIsInstance(data, list)

    def test_alerts_history(self):
        resp = self.client.get("/api/v1/alerts/history")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIsInstance(data, list)

    def test_quality_audit_endpoint(self):
        resp = self.client.get("/api/v1/quality/audit")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("is_monotonic", data)
        self.assertIn("solexs_availability_pct", data)

    def test_manifest_endpoint(self):
        resp = self.client.get("/api/v1/manifest")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIsInstance(data, list)

    def test_agent_status_endpoint(self):
        resp = self.client.get("/api/v1/agent/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["adapter_name"], "Agent37ResearchAdapter")
        self.assertIn("status", data)

    def test_compute_status_endpoint(self):
        resp = self.client.get("/api/v1/compute/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["adapter_name"], "NodusComputeAdapter")
        self.assertEqual(data["default_target"], "LOCAL_CPU")

    def test_cstlb_benchmark_endpoint(self):
        resp = self.client.get("/api/v1/benchmark/cstlb")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("benchmark_id", data)
        self.assertIn("scenario_results", data)


if __name__ == "__main__":
    unittest.main()
