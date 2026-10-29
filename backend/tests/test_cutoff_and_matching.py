"""Tests for decision cutoff resolution and forecast-to-actual matching engine.

Verifies:
1. Multiple forecast revisions for one delivery interval (picks latest at/before cutoff).
2. Forecast published exactly at the cutoff (included).
3. Forecast published after the cutoff (strictly excluded).
4. Timezone-aware UTC timestamp handling.
5. Missing actual and forecast records handling.
6. Duplicate and conflicting records detection.
7. December 2025 lookback forecasts matching January 2026 delivery.
"""

import unittest
from datetime import date, datetime, timedelta, timezone

from backend.elexon.models import FuelHHRecord
from backend.elexon.windfor import WindforRecord
from backend.engine.cutoff import get_cutoff_resolver
from backend.engine.matcher import match_actuals_and_forecasts


class TestCutoffResolution(unittest.TestCase):
    """Test cutoff resolver logic across different formats."""

    def test_day_ahead_1700_resolver(self):
        """Verify D-1 17:00 UTC cutoff for Jan 1, 2026 delivery."""
        resolver, name, desc = get_cutoff_resolver("day_ahead_1700")
        self.assertEqual(name, "day_ahead_1700")

        delivery = datetime(2026, 1, 1, 8, 30, tzinfo=timezone.utc)
        cutoff = resolver(delivery)

        expected = datetime(2025, 12, 31, 17, 0, tzinfo=timezone.utc)
        self.assertEqual(cutoff, expected)

    def test_day_ahead_1200_resolver(self):
        """Verify D-1 12:00 UTC cutoff."""
        resolver, name, _ = get_cutoff_resolver("day_ahead_1200")
        self.assertEqual(name, "day_ahead_1200")

        delivery = datetime(2026, 1, 5, 0, 0, tzinfo=timezone.utc)
        cutoff = resolver(delivery)
        expected = datetime(2026, 1, 4, 12, 0, tzinfo=timezone.utc)
        self.assertEqual(cutoff, expected)

    def test_gate_closure_resolver(self):
        """Verify 1-hour lead time gate closure cutoff."""
        resolver, name, _ = get_cutoff_resolver("gate_closure_1h")
        self.assertEqual(name, "gate_closure_1h")

        delivery = datetime(2026, 1, 1, 14, 0, tzinfo=timezone.utc)
        cutoff = resolver(delivery)
        expected = datetime(2026, 1, 1, 13, 0, tzinfo=timezone.utc)
        self.assertEqual(cutoff, expected)

    def test_absolute_iso_cutoff(self):
        """Verify absolute timestamp cutoff."""
        resolver, name, _ = get_cutoff_resolver("2025-12-31T20:00:00Z")
        self.assertEqual(name, "2025-12-31T20:00:00Z")

        delivery = datetime(2026, 1, 1, 4, 0, tzinfo=timezone.utc)
        cutoff = resolver(delivery)
        self.assertEqual(cutoff, datetime(2025, 12, 31, 20, 0, tzinfo=timezone.utc))

    def test_invalid_cutoff_raises_error(self):
        """Verify unsupported cutoff string raises ValueError."""
        with self.assertRaises(ValueError):
            get_cutoff_resolver("invalid_cutoff_rule_xyz")


class TestForecastActualMatching(unittest.TestCase):
    """Test forecast and actual matching engine."""

    def setUp(self):
        self.delivery_date = date(2026, 1, 1)
        self.delivery_slot = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)

    def test_multiple_forecast_revisions_selects_latest_before_cutoff(self):
        """Verify that out of multiple revisions, the latest before cutoff is chosen."""
        # Cutoff for 2026-01-01 under day_ahead_1700 is 2025-12-31 17:00:00Z
        forecasts = [
            # Revision 1: Published D-1 06:00
            WindforRecord(
                publishTime=datetime(2025, 12, 31, 6, 0, tzinfo=timezone.utc),
                startTime=self.delivery_slot,
                generation=5000.0,
            ),
            # Revision 2: Published D-1 14:00 (Latest before cutoff -> should be selected)
            WindforRecord(
                publishTime=datetime(2025, 12, 31, 14, 0, tzinfo=timezone.utc),
                startTime=self.delivery_slot,
                generation=5500.0,
            ),
            # Revision 3: Published D-1 18:00 (After cutoff -> must be excluded)
            WindforRecord(
                publishTime=datetime(2025, 12, 31, 18, 0, tzinfo=timezone.utc),
                startTime=self.delivery_slot,
                generation=6000.0,
            ),
        ]

        actuals = [
            FuelHHRecord(
                startTime=self.delivery_slot,
                settlementDate="2026-01-01",
                settlementPeriod=21,
                fuelType="WIND",
                generation=5400.0,
                publishTime=datetime(2026, 1, 1, 10, 45, tzinfo=timezone.utc),
            )
        ]

        dataset = match_actuals_and_forecasts(
            actuals=actuals,
            forecasts=forecasts,
            start_date=self.delivery_date,
            end_date=self.delivery_date,
            cutoff_param="day_ahead_1700",
        )

        matched = [inv for inv in dataset.intervals if inv.startTime == self.delivery_slot][0]
        self.assertEqual(matched.status, "matched")
        # Should pick revision 2 (5500.0 MW)
        self.assertEqual(matched.forecastGeneration, 5500.0)
        self.assertEqual(matched.forecastPublishTime, datetime(2025, 12, 31, 14, 0, tzinfo=timezone.utc))
        self.assertEqual(matched.actualGeneration, 5400.0)
        self.assertEqual(matched.signedError, 100.0)
        self.assertEqual(matched.absoluteError, 100.0)
        # Lead time: from 2025-12-31 14:00 to 2026-01-01 10:00 = 20 hours
        self.assertEqual(matched.leadTimeHours, 20.0)
        # Future forecast was filtered
        self.assertEqual(dataset.diagnostics.future_forecasts_filtered_count, 1)

    def test_forecast_published_exactly_at_cutoff_is_eligible(self):
        """Verify forecast published exactly at the cutoff timestamp is accepted."""
        cutoff_exact = datetime(2025, 12, 31, 17, 0, tzinfo=timezone.utc)
        forecasts = [
            WindforRecord(
                publishTime=cutoff_exact,
                startTime=self.delivery_slot,
                generation=7200.0,
            )
        ]
        actuals = [
            FuelHHRecord(
                startTime=self.delivery_slot,
                settlementDate="2026-01-01",
                settlementPeriod=21,
                fuelType="WIND",
                generation=7000.0,
                publishTime=datetime(2026, 1, 1, 10, 45, tzinfo=timezone.utc),
            )
        ]

        dataset = match_actuals_and_forecasts(
            actuals=actuals,
            forecasts=forecasts,
            start_date=self.delivery_date,
            end_date=self.delivery_date,
            cutoff_param="day_ahead_1700",
        )
        matched = [inv for inv in dataset.intervals if inv.startTime == self.delivery_slot][0]
        self.assertEqual(matched.status, "matched")
        self.assertEqual(matched.forecastGeneration, 7200.0)

    def test_forecast_published_one_second_after_cutoff_is_excluded(self):
        """Verify zero lookahead leakage: 1 second after cutoff is excluded."""
        cutoff_plus_1s = datetime(2025, 12, 31, 17, 0, 1, tzinfo=timezone.utc)
        forecasts = [
            WindforRecord(
                publishTime=cutoff_plus_1s,
                startTime=self.delivery_slot,
                generation=8000.0,
            )
        ]
        actuals = [
            FuelHHRecord(
                startTime=self.delivery_slot,
                settlementDate="2026-01-01",
                settlementPeriod=21,
                fuelType="WIND",
                generation=7000.0,
                publishTime=datetime(2026, 1, 1, 10, 45, tzinfo=timezone.utc),
            )
        ]

        dataset = match_actuals_and_forecasts(
            actuals=actuals,
            forecasts=forecasts,
            start_date=self.delivery_date,
            end_date=self.delivery_date,
            cutoff_param="day_ahead_1700",
        )
        matched = [inv for inv in dataset.intervals if inv.startTime == self.delivery_slot][0]
        # Should be missing_forecast because only forecast was after cutoff
        self.assertEqual(matched.status, "missing_forecast")
        self.assertIsNone(matched.forecastGeneration)
        self.assertEqual(dataset.diagnostics.future_forecasts_filtered_count, 1)

    def test_missing_actual_and_missing_forecast_statuses(self):
        """Verify statuses when actual or forecast is absent."""
        actual_only_slot = datetime(2026, 1, 1, 1, 0, tzinfo=timezone.utc)
        forecast_only_slot = datetime(2026, 1, 1, 2, 0, tzinfo=timezone.utc)

        actuals = [
            FuelHHRecord(
                startTime=actual_only_slot,
                settlementDate="2026-01-01",
                settlementPeriod=3,
                fuelType="WIND",
                generation=3000.0,
                publishTime=datetime(2026, 1, 1, 1, 45, tzinfo=timezone.utc),
            )
        ]
        forecasts = [
            WindforRecord(
                publishTime=datetime(2025, 12, 31, 16, 0, tzinfo=timezone.utc),
                startTime=forecast_only_slot,
                generation=4500.0,
            )
        ]

        dataset = match_actuals_and_forecasts(
            actuals=actuals,
            forecasts=forecasts,
            start_date=self.delivery_date,
            end_date=self.delivery_date,
            cutoff_param="day_ahead_1700",
        )

        item_actual_only = [inv for inv in dataset.intervals if inv.startTime == actual_only_slot][0]
        self.assertEqual(item_actual_only.status, "missing_forecast")
        self.assertIsNotNone(item_actual_only.actualGeneration)
        self.assertIsNone(item_actual_only.forecastGeneration)

        item_fc_only = [inv for inv in dataset.intervals if inv.startTime == forecast_only_slot][0]
        self.assertEqual(item_fc_only.status, "missing_actual")
        self.assertIsNone(item_fc_only.actualGeneration)
        self.assertIsNotNone(item_fc_only.forecastGeneration)

    def test_conflicting_actual_records_detection(self):
        """Verify multiple actual records for same slot are flagged as duplicate and conflicting."""
        slot = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
        actuals = [
            FuelHHRecord(
                startTime=slot,
                settlementDate="2026-01-01",
                settlementPeriod=25,
                fuelType="WIND",
                generation=5000.0,
                publishTime=datetime(2026, 1, 1, 12, 30, tzinfo=timezone.utc),
            ),
            FuelHHRecord(
                startTime=slot,
                settlementDate="2026-01-01",
                settlementPeriod=25,
                fuelType="WIND",
                generation=5200.0, # Conflict!
                publishTime=datetime(2026, 1, 1, 13, 00, tzinfo=timezone.utc),
            ),
        ]

        dataset = match_actuals_and_forecasts(
            actuals=actuals,
            forecasts=[],
            start_date=self.delivery_date,
            end_date=self.delivery_date,
        )

        self.assertEqual(dataset.diagnostics.duplicate_actual_records, 1)
        self.assertEqual(dataset.diagnostics.conflicting_actual_records, 1)
        self.assertTrue(len(dataset.diagnostics.warnings) > 0)


if __name__ == "__main__":
    unittest.main()

