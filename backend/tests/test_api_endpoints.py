"""Integration tests for FastAPI endpoints using TestClient with injected mock data."""

import unittest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from backend.api.routes import set_data_service
from backend.elexon.models import FuelHHRecord
from backend.elexon.windfor import WindforRecord
from backend.main import app
from backend.services.data_service import DataService


class TestAPIEndpoints(unittest.TestCase):
    """Test suite for WindLens FastAPI endpoints."""

    @classmethod
    def setUpClass(cls):
        # Build mock data service preloaded with synthetic test records
        cls.mock_service = DataService(enable_disk_cache=False)

        # Inject sample delivery slots for 2026-01-01 (first 2 hours: 00:00, 00:30, 01:00, 01:30)
        sample_slots = [
            datetime(2026, 1, 1, h, m, tzinfo=timezone.utc)
            for h in range(2) for m in (0, 30)
        ]

        actuals = [
            FuelHHRecord(
                startTime=st,
                settlementDate="2026-01-01",
                settlementPeriod=idx + 1,
                fuelType="WIND",
                generation=3000.0 + idx * 200.0,
                publishTime=st + (datetime(2026, 1, 1, 1, 0, tzinfo=timezone.utc) - datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)),
            )
            for idx, st in enumerate(sample_slots)
        ]

        # Forecasts published at D-1 15:00 UTC (before day_ahead_1700 cutoff) for 00:00 and 01:00
        forecasts = [
            WindforRecord(
                publishTime=datetime(2025, 12, 31, 15, 0, tzinfo=timezone.utc),
                startTime=datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc),
                generation=3100.0,
            ),
            WindforRecord(
                publishTime=datetime(2025, 12, 31, 15, 0, tzinfo=timezone.utc),
                startTime=datetime(2026, 1, 1, 1, 0, tzinfo=timezone.utc),
                generation=3500.0,
            ),
        ]

        cls.mock_service.load_records_into_cache(actuals=actuals, forecasts=forecasts)
        set_data_service(cls.mock_service)
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        set_data_service(None)

    def test_health_endpoint(self):
        """GET /api/health returns status 200 and expected payload."""
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["app"], "WindLens")
        self.assertEqual(data["version"], "0.2.0")
        self.assertIn("timestamp", data)

    def test_overview_endpoint_success_hourly(self):
        """GET /api/overview returns daily metrics with hourly resolution."""
        resp = self.client.get("/api/overview?date=2026-01-01&cutoff=day_ahead_1700&resolution=hourly")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["date"], "2026-01-01")
        self.assertEqual(data["cutoff"], "day_ahead_1700")
        self.assertEqual(data["resolution"], "hourly")
        self.assertIn("metrics", data)
        self.assertIn("actualSummary", data)
        self.assertIn("forecastSummary", data)
        self.assertIn("diagnostics", data)
        self.assertIn("methodology", data)
        self.assertGreaterEqual(data["metrics"]["matched_intervals_count"], 2)

    def test_overview_invalid_date_format_returns_400(self):
        """GET /api/overview with malformed date parameter returns HTTP 400."""
        resp = self.client.get("/api/overview?date=not-a-date")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Invalid date format", resp.json()["detail"])

    def test_overview_invalid_resolution_returns_400(self):
        """GET /api/overview with invalid resolution returns HTTP 400."""
        resp = self.client.get("/api/overview?date=2026-01-01&resolution=minutely")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Unsupported resolution", resp.json()["detail"])

    def test_timeseries_endpoint_hourly_default(self):
        """GET /api/timeseries defaults to hourly alignment (24 intervals in full day)."""
        resp = self.client.get("/api/timeseries?date=2026-01-01&cutoff=day_ahead_1700")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["date"], "2026-01-01")
        self.assertEqual(data["resolution"], "hourly")
        self.assertIn("intervals", data)
        self.assertEqual(len(data["intervals"]), 24)  # 24 clock-hour intervals in full day

        matched_items = [i for i in data["intervals"] if i["status"] == "matched"]
        self.assertEqual(len(matched_items), 2)
        sample = matched_items[0]
        self.assertIn("signedError", sample)
        self.assertIn("absoluteError", sample)
        self.assertIn("leadTimeHours", sample)
        self.assertIn("forecastPublishTime", sample)
        self.assertIn("actualPublishTime", sample)

    def test_timeseries_endpoint_half_hourly_view(self):
        """GET /api/timeseries with resolution=half_hourly returns 48 slots and labels :30 as resolution_mismatch."""
        resp = self.client.get("/api/timeseries?date=2026-01-01&cutoff=day_ahead_1700&resolution=half_hourly")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["resolution"], "half_hourly")
        self.assertEqual(len(data["intervals"]), 48)

        mismatches = [i for i in data["intervals"] if i["status"] == "resolution_mismatch"]
        self.assertEqual(len(mismatches), 24)

    def test_timeseries_invalid_cutoff_returns_400(self):
        """GET /api/timeseries with invalid cutoff returns HTTP 400."""
        resp = self.client.get("/api/timeseries?date=2026-01-01&cutoff=unsupported_cutoff_xyz")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Unsupported cutoff format", resp.json()["detail"])

    def test_accuracy_range_endpoint_success(self):
        """GET /api/accuracy returns overall metrics and daily breakdown."""
        resp = self.client.get("/api/accuracy?from=2026-01-01&to=2026-01-02&cutoff=day_ahead_1700&resolution=hourly")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["fromDate"], "2026-01-01")
        self.assertEqual(data["toDate"], "2026-01-02")
        self.assertEqual(data["resolution"], "hourly")
        self.assertIn("metrics", data)
        self.assertIn("dailyBreakdown", data)
        self.assertEqual(len(data["dailyBreakdown"]), 2)

    def test_accuracy_range_invalid_range_returns_400(self):
        """GET /api/accuracy with to < from returns HTTP 400."""
        resp = self.client.get("/api/accuracy?from=2026-01-05&to=2026-01-01")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("must be on or after", resp.json()["detail"])

    def test_root_endpoint(self):
        """GET / returns API discovery metadata."""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["app"], "WindLens")


if __name__ == "__main__":
    unittest.main()
