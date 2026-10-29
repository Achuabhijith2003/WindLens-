"""Tests for DataService cache behavior, disk persistence, and safe API error propagation."""

import shutil
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
import httpx

from backend.elexon.client import ElexonClient, ElexonHTTPStatusError, ElexonTimeoutError
from backend.elexon.models import FuelHHRecord
from backend.elexon.windfor import WindforRecord
from backend.services.data_service import DataService


class TestServiceAndCache(unittest.TestCase):
    """Test suite for DataService caching and failure handling."""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_disk_cache_persistence_and_reloading(self):
        """Verify records are written to disk and reloaded by a new DataService instance."""
        service1 = DataService(cache_dir=self.temp_dir, enable_disk_cache=True)

        slot = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        actual = FuelHHRecord(
            startTime=slot,
            settlementDate="2026-01-01",
            settlementPeriod=1,
            fuelType="WIND",
            generation=4500.0,
            publishTime=datetime(2026, 1, 1, 0, 45, tzinfo=timezone.utc),
        )
        forecast = WindforRecord(
            publishTime=datetime(2025, 12, 31, 15, 0, tzinfo=timezone.utc),
            startTime=slot,
            generation=4600.0,
        )

        service1.load_records_into_cache(actuals=[actual], forecasts=[forecast])
        service1._save_disk_cache()

        # Check files were created on disk
        self.assertTrue((self.temp_dir / "fuelhh_cache.json").exists())
        self.assertTrue((self.temp_dir / "windfor_cache.json").exists())

        # Create new service pointing to the same cache directory
        service2 = DataService(cache_dir=self.temp_dir, enable_disk_cache=True)
        self.assertEqual(len(service2._actuals_cache), 1)
        self.assertEqual(len(service2._forecasts_cache), 1)

        cached_actuals = service2.fetch_actuals_for_delivery_dates(date(2026, 1, 1), date(2026, 1, 1))
        self.assertEqual(len(cached_actuals), 1)
        self.assertEqual(cached_actuals[0].generation, 4500.0)

    def test_api_failure_raises_error_without_synthetic_substitution(self):
        """Verify API errors are raised and no synthetic or fabricated data is substituted."""
        def failing_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(503, text="Service Unavailable: BMRS Maintenance")

        client = httpx.Client(transport=httpx.MockTransport(failing_handler))
        elexon_client = ElexonClient(client=client)

        service = DataService(client=elexon_client, cache_dir=self.temp_dir, enable_disk_cache=False)

        # Attempting to fetch actuals when cache is empty must raise, NOT fabricate data
        with self.assertRaises(ElexonHTTPStatusError):
            service.fetch_actuals_for_delivery_dates(date(2026, 1, 1), date(2026, 1, 1))

        # Cache must remain empty
        self.assertEqual(len(service._actuals_cache), 0)

    def test_api_timeout_raises_without_synthetic_substitution(self):
        """Verify API timeouts are raised and no synthetic or fabricated data is substituted."""
        def timeout_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("Timeout connecting to Elexon", request=request)

        client = httpx.Client(transport=httpx.MockTransport(timeout_handler))
        elexon_client = ElexonClient(client=client)

        service = DataService(client=elexon_client, cache_dir=self.temp_dir, enable_disk_cache=False)

        with self.assertRaises(ElexonTimeoutError):
            service.fetch_forecasts_for_delivery_dates(date(2026, 1, 1), date(2026, 1, 1))

        self.assertEqual(len(service._forecasts_cache), 0)

    def test_empty_api_results_handled_safely(self):
        """Verify empty API responses do not crash and result in empty cache."""
        def empty_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=[])

        client = httpx.Client(transport=httpx.MockTransport(empty_handler))
        elexon_client = ElexonClient(client=client)

        service = DataService(client=elexon_client, cache_dir=self.temp_dir, enable_disk_cache=False)

        actuals = service.fetch_actuals_for_delivery_dates(date(2026, 1, 1), date(2026, 1, 1))
        self.assertEqual(len(actuals), 0)

    def test_partial_cache_fetches_missing_dates(self):
        """Verify that when only some dates are cached, the missing dates trigger an API fetch."""
        calls = []
        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(str(request.url))
            # Return empty list
            return httpx.Response(200, json=[])

        client = httpx.Client(transport=httpx.MockTransport(handler))
        elexon_client = ElexonClient(client=client)
        service = DataService(client=elexon_client, cache_dir=self.temp_dir, enable_disk_cache=False)

        # Pre-cache Jan 1 only
        rec1 = FuelHHRecord(
            startTime=datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc),
            settlementDate="2026-01-01",
            settlementPeriod=1,
            fuelType="WIND",
            generation=4000.0,
            publishTime=datetime(2026, 1, 1, 0, 30, tzinfo=timezone.utc),
        )
        service.load_records_into_cache(actuals=[rec1])

        # If we query Jan 1 only, it should hit cache and make NO API calls
        res_jan1 = service.fetch_actuals_for_delivery_dates(date(2026, 1, 1), date(2026, 1, 1))
        self.assertEqual(len(res_jan1), 1)
        self.assertEqual(len(calls), 0)

        # If we query Jan 1 to Jan 2, Jan 2 is missing, so it should trigger an API call
        service.fetch_actuals_for_delivery_dates(date(2026, 1, 1), date(2026, 1, 2))
        self.assertGreater(len(calls), 0)


if __name__ == "__main__":
    unittest.main()

