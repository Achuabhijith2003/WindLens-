"""Audit verification test suite:
1. Validates default cutoff is day_ahead_1700 across routes and resolvers.
2. Validates independent recalculation of MAE, RMSE, Signed Bias, and MAPE directly against matched records.
3. Validates that hourly forecasts are NEVER fabricated into half-hourly slots.
4. Validates edge cases: empty data, zero actuals for MAPE, error states.
"""

import math
import unittest
from datetime import date, datetime, timezone
from fastapi.testclient import TestClient

from backend.main import app
from backend.api.routes import set_data_service
from backend.services.data_service import DataService
from backend.engine.cutoff import DEFAULT_CUTOFF, get_cutoff_resolver
from backend.elexon.models import FuelHHRecord
from backend.elexon.windfor import WindforRecord


class TestAuditVerification(unittest.TestCase):
    """Rigorous audit verification test suite for deployment readiness."""

    @classmethod
    def setUpClass(cls):
        # Use live data service instance backed by data/cache
        cls.service = DataService(enable_disk_cache=True)
        set_data_service(cls.service)
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        set_data_service(None)

    def test_item_1_default_cutoff_is_day_ahead_1700(self):
        """Audit Item 1: Confirm day_ahead_1700 is the default cutoff everywhere."""
        self.assertEqual(DEFAULT_CUTOFF, "day_ahead_1700")

        resolver, canonical, desc = get_cutoff_resolver(None)
        self.assertEqual(canonical, "day_ahead_1700")
        self.assertIn("D-1", desc)
        self.assertIn("17:00", desc)

        # Confirm API route default
        resp = self.client.get("/api/overview?date=2026-01-01")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["cutoff"], "day_ahead_1700")

    def test_item_2_and_3_verify_metrics_independently_against_matched_records(self):
        """Audit Item 3: Independently verify MAE, RMSE, Bias, and MAPE against returned records."""
        # Query timeseries for 2026-01-01 under default cutoff and hourly resolution
        ts_resp = self.client.get("/api/timeseries?date=2026-01-01&cutoff=day_ahead_1700&resolution=hourly")
        self.assertEqual(ts_resp.status_code, 200)
        ts_data = ts_resp.json()

        ov_resp = self.client.get("/api/overview?date=2026-01-01&cutoff=day_ahead_1700&resolution=hourly")
        self.assertEqual(ov_resp.status_code, 200)
        ov_data = ov_resp.json()

        intervals = ts_data["intervals"]
        matched_intervals = [
            i for i in intervals
            if i["status"] == "matched" and i["actualGeneration"] is not None and i["forecastGeneration"] is not None
        ]

        self.assertEqual(len(matched_intervals), 24)
        self.assertEqual(ov_data["diagnostics"]["matched_intervals_count"], 24)

        # Independent manual calculation
        signed_errors = []
        abs_errors = []
        sq_errors = []
        pct_errors = []
        zero_count = 0

        for item in matched_intervals:
            act = item["actualGeneration"]
            fc = item["forecastGeneration"]
            err = fc - act

            # Confirm per-interval error matches
            self.assertAlmostEqual(item["signedError"], round(err, 2), places=2)
            self.assertAlmostEqual(item["absoluteError"], round(abs(err), 2), places=2)

            signed_errors.append(err)
            abs_errors.append(abs(err))
            sq_errors.append(err ** 2)

            if act != 0:
                pct_err = abs(err) / abs(act) * 100.0
                pct_errors.append(pct_err)
                self.assertAlmostEqual(item["percentageError"], round(pct_err, 2), places=2)
            else:
                zero_count += 1
                self.assertIsNone(item["percentageError"])

        n = len(matched_intervals)
        expected_mae = sum(abs_errors) / n
        expected_rmse = math.sqrt(sum(sq_errors) / n)
        expected_bias = sum(signed_errors) / n
        expected_mape = sum(pct_errors) / len(pct_errors) if pct_errors else None

        reported_metrics = ov_data["metrics"]
        self.assertAlmostEqual(reported_metrics["mae_mw"], round(expected_mae, 2), places=2)
        self.assertAlmostEqual(reported_metrics["rmse_mw"], round(expected_rmse, 2), places=2)
        self.assertAlmostEqual(reported_metrics["signed_bias_mw"], round(expected_bias, 2), places=2)
        self.assertAlmostEqual(reported_metrics["mape_pct"], round(expected_mape, 2), places=2)
        self.assertEqual(reported_metrics["mape_excluded_zero_count"], zero_count)

    def test_item_4_hourly_forecasts_not_fabricated_into_half_hourly_slots(self):
        """Audit Item 4: Confirm that :30 slots in half-hourly mode NEVER fabricate forecasts."""
        resp = self.client.get("/api/timeseries?date=2026-01-01&cutoff=day_ahead_1700&resolution=half_hourly")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        intervals = data["intervals"]
        self.assertEqual(len(intervals), 48)

        # Check every interval:
        # If minute == 30: forecast MUST be None, status MUST be resolution_mismatch
        mismatch_count = 0
        matched_count = 0
        for item in intervals:
            st = datetime.fromisoformat(item["startTime"])
            if st.minute == 30:
                self.assertIsNone(item["forecastGeneration"], f"Forecast fabricated for {item['startTime']}!")
                self.assertIsNone(item["forecastPublishTime"])
                self.assertIsNone(item["leadTimeHours"])
                self.assertIsNone(item["signedError"])
                self.assertEqual(item["status"], "resolution_mismatch")
                mismatch_count += 1
            elif st.minute == 0:
                self.assertIsNotNone(item["forecastGeneration"])
                self.assertEqual(item["status"], "matched")
                matched_count += 1

        self.assertEqual(mismatch_count, 24)
        self.assertEqual(matched_count, 24)

    def test_item_5_empty_data_and_error_states(self):
        """Audit Item 5: Check API error handling and empty data boundaries."""
        # 1. Invalid date format
        resp = self.client.get("/api/overview?date=invalid-date")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Invalid date format", resp.json()["detail"])

        # 2. Invalid cutoff
        resp = self.client.get("/api/overview?date=2026-01-01&cutoff=invalid_cutoff")
        self.assertEqual(resp.status_code, 400)

        # 3. Invalid resolution
        resp = self.client.get("/api/overview?date=2026-01-01&resolution=quarter_hourly")
        self.assertEqual(resp.status_code, 400)

        # 4. Out of range future date with no data returns empty/missing intervals without crashing
        resp = self.client.get("/api/timeseries?date=2035-01-01")
        # Should return 200 with missing intervals
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data["intervals"]), 24)
        for i in data["intervals"]:
            self.assertEqual(i["status"], "missing_both")


if __name__ == "__main__":
    unittest.main()
