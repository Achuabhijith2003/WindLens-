"""Unit tests for FUELHH exploration and WINDFOR investigation modules.

Uses mocked API responses via HTTPX MockTransport to verify:
1. Retrieval and parsing of FUELHH stream records.
2. Filtering to WIND and validation of required fields.
3. Manageable date window partitioning.
4. Publication-time window vs delivery-time window independence.
5. Reporting of record counts, missing fields, duplicate startTimes, and min/max startTimes.
6. HTTP timeout and status error handling.
7. WINDFOR horizon and revision characteristics.
"""

from __future__ import annotations

import json
import unittest
from datetime import datetime, timedelta, timezone
import httpx

from backend.elexon.client import (
    ElexonClient,
    ElexonTimeoutError,
    ElexonHTTPStatusError,
    ElexonConnectionError,
    format_iso8601_utc,
)
from backend.elexon.fuelhh import (
    analyze_fuelhh_records,
    fetch_fuelhh_windowed,
    generate_date_windows,
)
from backend.elexon.models import FuelHHRecord
from backend.elexon.windfor import analyze_windfor_records, WindforRecord


class TestFuelHHExploration(unittest.TestCase):
    """Test suite for FUELHH exploration and validation."""

    def test_fuelhh_success_with_mock_transport(self):
        """Verify successful stream retrieval and WIND filtering with mocked HTTPX."""
        mock_records = [
            {
                "dataset": "FUELHH",
                "publishTime": "2026-01-01T00:30:00Z",
                "startTime": "2026-01-01T00:00:00Z",
                "settlementDate": "2026-01-01",
                "settlementPeriod": 1,
                "fuelType": "WIND",
                "generation": 3450.5,
            },
            {
                "dataset": "FUELHH",
                "publishTime": "2026-01-01T01:00:00Z",
                "startTime": "2026-01-01T00:30:00Z",
                "settlementDate": "2026-01-01",
                "settlementPeriod": 2,
                "fuelType": "WIND",
                "generation": 3600.0,
            },
            {
                # Non-WIND record that should be filtered out
                "dataset": "FUELHH",
                "publishTime": "2026-01-01T00:30:00Z",
                "startTime": "2026-01-01T00:00:00Z",
                "settlementDate": "2026-01-01",
                "settlementPeriod": 1,
                "fuelType": "CCGT",
                "generation": 9800.0,
            },
        ]

        def handler(request: httpx.Request) -> httpx.Response:
            self.assertIn("datasets/FUELHH/stream", str(request.url))
            self.assertIn("fuelType=WIND", str(request.url))
            return httpx.Response(200, json=mock_records)

        client = httpx.Client(transport=httpx.MockTransport(handler))
        elexon_client = ElexonClient(client=client)

        start = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 1, 1, 2, 0, tzinfo=timezone.utc)

        records = elexon_client.fetch_fuelhh_stream(start, end, fuel_type="WIND")
        self.assertEqual(len(records), 3)

        valid_records, report = analyze_fuelhh_records(records, start, end)

        self.assertEqual(report.total_records_received, 3)
        self.assertEqual(report.wind_records_count, 2)
        self.assertEqual(report.non_wind_records_count, 1)
        self.assertEqual(report.valid_records_count, 2)
        self.assertEqual(report.invalid_records_count, 0)
        self.assertEqual(len(valid_records), 2)
        self.assertEqual(report.min_start_time, "2026-01-01T00:00:00Z")
        self.assertEqual(report.max_start_time, "2026-01-01T00:30:00Z")
        self.assertEqual(report.generation_stats["min_mw"], 3450.5)
        self.assertEqual(report.generation_stats["max_mw"], 3600.0)

    def test_window_generation_and_windowed_retrieval(self):
        """Verify partitioning January 2026 into manageable date windows."""
        start = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 1, 5, 0, 0, tzinfo=timezone.utc)

        windows = generate_date_windows(start, end, window_size=timedelta(days=2))
        self.assertEqual(len(windows), 2)
        self.assertEqual(windows[0], (start, datetime(2026, 1, 3, 0, 0, tzinfo=timezone.utc)))
        self.assertEqual(windows[1], (datetime(2026, 1, 3, 0, 0, tzinfo=timezone.utc), end))

        calls_received: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls_received.append(str(request.url))
            chunk = [
                {
                    "dataset": "FUELHH",
                    "publishTime": "2026-01-01T12:00:00Z",
                    "startTime": "2026-01-01T11:30:00Z",
                    "settlementDate": "2026-01-01",
                    "settlementPeriod": 24,
                    "fuelType": "WIND",
                    "generation": 5000.0,
                }
            ]
            return httpx.Response(200, json=chunk)

        client = httpx.Client(transport=httpx.MockTransport(handler))
        elexon_client = ElexonClient(client=client)

        valid_records, global_report = fetch_fuelhh_windowed(
            client=elexon_client,
            start=start,
            end=end,
            window_size=timedelta(days=2),
        )

        self.assertEqual(len(calls_received), 2)
        self.assertEqual(len(valid_records), 2)
        self.assertEqual(len(global_report.window_reports), 2)

    def test_missing_fields_and_invalid_records_detection(self):
        """Verify validation catches missing fields and non-numeric values."""
        malformed_records = [
            {
                # Missing settlementDate and generation
                "dataset": "FUELHH",
                "publishTime": "2026-01-01T00:30:00Z",
                "startTime": "2026-01-01T00:00:00Z",
                "settlementPeriod": 1,
                "fuelType": "WIND",
            },
            {
                # generation is non-numeric string
                "dataset": "FUELHH",
                "publishTime": "2026-01-01T01:00:00Z",
                "startTime": "2026-01-01T00:30:00Z",
                "settlementDate": "2026-01-01",
                "settlementPeriod": 2,
                "fuelType": "WIND",
                "generation": "NOT_A_NUMBER",
            },
            {
                # Invalid datetime format for startTime
                "dataset": "FUELHH",
                "publishTime": "2026-01-01T01:30:00Z",
                "startTime": "bad-timestamp",
                "settlementDate": "2026-01-01",
                "settlementPeriod": 3,
                "fuelType": "WIND",
                "generation": 4000.0,
            },
        ]

        start = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 1, 1, 2, 0, tzinfo=timezone.utc)

        valid_records, report = analyze_fuelhh_records(malformed_records, start, end)

        self.assertEqual(report.valid_records_count, 0)
        self.assertEqual(report.invalid_records_count, 3)
        self.assertIn("settlementDate", report.missing_fields_summary)
        self.assertIn("generation", report.missing_fields_summary)
        self.assertIn("generation_not_numeric", report.missing_fields_summary)
        self.assertIn("startTime_invalid_format", report.missing_fields_summary)

    def test_duplicate_start_times_detection(self):
        """Verify duplicate startTime timestamps are detected and reported."""
        records_with_duplicates = [
            {
                "dataset": "FUELHH",
                "publishTime": "2026-01-01T01:00:00Z",
                "startTime": "2026-01-01T00:00:00Z",  # Duplicate 1
                "settlementDate": "2026-01-01",
                "settlementPeriod": 1,
                "fuelType": "WIND",
                "generation": 3100.0,
            },
            {
                "dataset": "FUELHH",
                "publishTime": "2026-01-01T01:30:00Z",
                "startTime": "2026-01-01T00:00:00Z",  # Duplicate 2 (e.g. revision)
                "settlementDate": "2026-01-01",
                "settlementPeriod": 1,
                "fuelType": "WIND",
                "generation": 3150.0,
            },
            {
                "dataset": "FUELHH",
                "publishTime": "2026-01-01T01:30:00Z",
                "startTime": "2026-01-01T00:30:00Z",  # Unique
                "settlementDate": "2026-01-01",
                "settlementPeriod": 2,
                "fuelType": "WIND",
                "generation": 3200.0,
            },
        ]

        start = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 1, 1, 2, 0, tzinfo=timezone.utc)

        valid_records, report = analyze_fuelhh_records(records_with_duplicates, start, end)

        self.assertEqual(report.valid_records_count, 3)
        self.assertEqual(report.duplicate_start_time_count, 1)
        self.assertIn("2026-01-01T00:00:00Z", report.duplicate_start_times)

    def test_publication_vs_delivery_time_independence(self):
        """Verify publication window does NOT assume equality with delivery window."""
        records = [
            {
                # Delivery interval is 2025-12-31 23:30, published on 2026-01-01 00:15
                "dataset": "FUELHH",
                "publishTime": "2026-01-01T00:15:00Z",
                "startTime": "2025-12-31T23:30:00Z",
                "settlementDate": "2025-12-31",
                "settlementPeriod": 48,
                "fuelType": "WIND",
                "generation": 2800.0,
            },
            {
                # Delivery interval is 2026-01-01 00:00, published on 2026-01-01 00:45
                "dataset": "FUELHH",
                "publishTime": "2026-01-01T00:45:00Z",
                "startTime": "2026-01-01T00:00:00Z",
                "settlementDate": "2026-01-01",
                "settlementPeriod": 1,
                "fuelType": "WIND",
                "generation": 2900.0,
            },
        ]

        # Publication window is Jan 1 00:00 to 01:00
        pub_from = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        pub_to = datetime(2026, 1, 1, 1, 0, tzinfo=timezone.utc)

        valid_records, report = analyze_fuelhh_records(records, pub_from, pub_to)

        # min_start_time is in 2025, which precedes the publication window start!
        self.assertEqual(report.min_start_time, "2025-12-31T23:30:00Z")
        self.assertEqual(report.min_publish_time, "2026-01-01T00:15:00Z")
        self.assertNotEqual(report.min_start_time, report.query_publish_from)

    def test_httpx_timeout_handling(self):
        """Verify clear error handling for HTTP timeouts."""
        def timeout_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("Read timed out after 30s", request=request)

        client = httpx.Client(transport=httpx.MockTransport(timeout_handler))
        elexon_client = ElexonClient(client=client)

        start = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 1, 1, 1, 0, tzinfo=timezone.utc)

        with self.assertRaises(ElexonTimeoutError) as ctx:
            elexon_client.fetch_fuelhh_stream(start, end)
        self.assertIn("timed out", str(ctx.exception).lower())

    def test_httpx_status_error_handling(self):
        """Verify clear error handling for HTTP status errors (e.g. 500)."""
        def error_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="Internal Server Error: Database failure")

        client = httpx.Client(transport=httpx.MockTransport(error_handler))
        elexon_client = ElexonClient(client=client)

        start = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 1, 1, 1, 0, tzinfo=timezone.utc)

        with self.assertRaises(ElexonHTTPStatusError) as ctx:
            elexon_client.fetch_fuelhh_stream(start, end)
        self.assertEqual(ctx.exception.status_code, 500)
        self.assertIn("500", str(ctx.exception))

    def test_windfor_investigation_and_lead_times(self):
        """Verify WINDFOR investigation detects forecast horizons and lead times."""
        # Simulate forecast run published on 2025-12-31 17:00 forecasting Jan 1 00:00 and 01:00
        mock_windfor = [
            {
                "dataset": "WINDFOR",
                "publishTime": "2025-12-31T17:00:00Z",
                "startTime": "2026-01-01T00:00:00Z",
                "generation": 5200,
            },
            {
                "dataset": "WINDFOR",
                "publishTime": "2025-12-31T17:00:00Z",
                "startTime": "2026-01-01T01:00:00Z",
                "generation": 5300,
            },
            {
                # Second run on 2025-12-31 21:00 revising the same Jan 1 00:00 slot
                "dataset": "WINDFOR",
                "publishTime": "2025-12-31T21:00:00Z",
                "startTime": "2026-01-01T00:00:00Z",
                "generation": 5250,
            },
        ]

        pub_start = datetime(2025, 12, 31, 16, 0, tzinfo=timezone.utc)
        pub_end = datetime(2025, 12, 31, 22, 0, tzinfo=timezone.utc)

        valid_records, report = analyze_windfor_records(mock_windfor, pub_start, pub_end)

        self.assertEqual(report.valid_records_count, 3)
        self.assertEqual(report.unique_publish_runs, 2)
        self.assertEqual(report.unique_delivery_start_times, 2)
        # Lead times: 2026-01-01 00:00 vs 2025-12-31 21:00 is 3h; 2026-01-01 01:00 vs 2025-12-31 17:00 is 8h
        self.assertEqual(report.min_lead_time_hours, 3.0)
        self.assertEqual(report.max_lead_time_hours, 8.0)
        # Delivery times (Jan 1) extend beyond publication window (Dec 31)
        self.assertTrue(report.delivery_extends_beyond_query_window)
        self.assertTrue(len(report.findings_and_uncertainties) > 0)


if __name__ == "__main__":
    unittest.main()

