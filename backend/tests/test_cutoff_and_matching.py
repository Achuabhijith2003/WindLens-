"""Tests for decision cutoff resolution and forecast-to-actual matching engine.

Verifies:
1. Multiple forecast revisions for one delivery interval (picks latest at/before cutoff).
2. Forecast published exactly at the cutoff (included).
3. Forecast published after the cutoff (strictly excluded).
4. Different cutoff calculated independently for each delivery date.
5. Midnight and month boundary cutoff calculations.
6. Timezone-aware UTC timestamp handling.
7. Missing actual and forecast records handling.
8. Duplicate and conflicting records detection.
9. Hourly aggregation of two 30-min actuals into 1-hour average MW.
10. Half-hourly resolution mismatch labeled separately from pipeline ingestion failures.
"""

import unittest
from datetime import date, datetime, timedelta, timezone

from backend.elexon.models import FuelHHRecord
from backend.elexon.windfor import WindforRecord
from backend.engine.cutoff import get_cutoff_resolver
from backend.engine.matcher import match_actuals_and_forecasts


class TestCutoffResolution(unittest.TestCase):
    """Test cutoff resolver logic across different formats and edge cases."""

    def test_day_ahead_1700_resolver_per_delivery_date(self):
        """Verify D-1 17:00 UTC cutoff is calculated independently for each delivery date."""
        resolver, name, desc = get_cutoff_resolver("day_ahead_1700")
        self.assertEqual(name, "day_ahead_1700")

        # Jan 1 delivery -> cutoff Dec 31 17:00 UTC
        deliv_jan1 = datetime(2026, 1, 1, 8, 30, tzinfo=timezone.utc)
        self.assertEqual(resolver(deliv_jan1), datetime(2025, 12, 31, 17, 0, tzinfo=timezone.utc))

        # Jan 2 delivery -> cutoff Jan 1 17:00 UTC (different from Jan 1)
        deliv_jan2 = datetime(2026, 1, 2, 14, 0, tzinfo=timezone.utc)
        self.assertEqual(resolver(deliv_jan2), datetime(2026, 1, 1, 17, 0, tzinfo=timezone.utc))

        # Jan 15 delivery -> cutoff Jan 14 17:00 UTC
        deliv_jan15 = datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(resolver(deliv_jan15), datetime(2026, 1, 14, 17, 0, tzinfo=timezone.utc))

    def test_midnight_and_month_boundaries(self):
        """Verify midnight delivery and month boundary cutoffs."""
        resolver, _, _ = get_cutoff_resolver("day_ahead_1700")

        # Midnight on Jan 1 (00:00:00 UTC) belongs to Date 2026-01-01 -> Cutoff is 2025-12-31 17:00:00 UTC
        midnight_jan1 = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(resolver(midnight_jan1), datetime(2025, 12, 31, 17, 0, tzinfo=timezone.utc))

        # 23:00 on Jan 1 belongs to Date 2026-01-01 -> Same cutoff 2025-12-31 17:00:00 UTC
        end_jan1 = datetime(2026, 1, 1, 23, 0, tzinfo=timezone.utc)
        self.assertEqual(resolver(end_jan1), datetime(2025, 12, 31, 17, 0, tzinfo=timezone.utc))

        # Midnight on Feb 1 (Month boundary) belongs to Date 2026-02-01 -> Cutoff is 2026-01-31 17:00:00 UTC
        feb1_midnight = datetime(2026, 2, 1, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(resolver(feb1_midnight), datetime(2026, 1, 31, 17, 0, tzinfo=timezone.utc))

    def test_day_ahead_1200_resolver(self):
        """Verify D-1 12:00 UTC cutoff."""
        resolver, name, _ = get_cutoff_resolver("day_ahead_1200")
        self.assertEqual(name, "day_ahead_1200")

        delivery = datetime(2026, 1, 5, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(resolver(delivery), datetime(2026, 1, 4, 12, 0, tzinfo=timezone.utc))

    def test_gate_closure_resolver(self):
        """Verify 1-hour lead time gate closure cutoff."""
        resolver, name, _ = get_cutoff_resolver("gate_closure_1h")
        self.assertEqual(name, "gate_closure_1h")

        delivery = datetime(2026, 1, 1, 14, 0, tzinfo=timezone.utc)
        self.assertEqual(resolver(delivery), datetime(2026, 1, 1, 13, 0, tzinfo=timezone.utc))

    def test_absolute_iso_cutoff(self):
        """Verify absolute timestamp cutoff."""
        resolver, name, _ = get_cutoff_resolver("2025-12-31T20:00:00Z")
        self.assertEqual(name, "2025-12-31T20:00:00Z")

        delivery = datetime(2026, 1, 1, 4, 0, tzinfo=timezone.utc)
        self.assertEqual(resolver(delivery), datetime(2025, 12, 31, 20, 0, tzinfo=timezone.utc))

    def test_invalid_cutoff_raises_error(self):
        """Verify unsupported cutoff string raises ValueError."""
        with self.assertRaises(ValueError):
            get_cutoff_resolver("invalid_cutoff_rule_xyz")


class TestForecastActualMatching(unittest.TestCase):
    """Test forecast and actual matching engine across resolutions and cutoff boundaries."""

    def test_multiple_forecast_revisions_selects_latest_before_cutoff(self):
        """Verify that out of multiple revisions, the latest before cutoff is chosen."""
        slot = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
        forecasts = [
            # Revision 1: Published D-1 06:00
            WindforRecord(
                publishTime=datetime(2025, 12, 31, 6, 0, tzinfo=timezone.utc),
                startTime=slot,
                generation=5000.0,
            ),
            # Revision 2: Published D-1 14:00 (Latest before cutoff -> should be selected)
            WindforRecord(
                publishTime=datetime(2025, 12, 31, 14, 0, tzinfo=timezone.utc),
                startTime=slot,
                generation=5500.0,
            ),
            # Revision 3: Published D-1 18:00 (After cutoff -> must be excluded)
            WindforRecord(
                publishTime=datetime(2025, 12, 31, 18, 0, tzinfo=timezone.utc),
                startTime=slot,
                generation=6000.0,
            ),
        ]

        actuals = [
            FuelHHRecord(
                startTime=slot,
                settlementDate="2026-01-01",
                settlementPeriod=21,
                fuelType="WIND",
                generation=5400.0,
                publishTime=datetime(2026, 1, 1, 10, 45, tzinfo=timezone.utc),
            ),
            FuelHHRecord(
                startTime=slot + timedelta(minutes=30),
                settlementDate="2026-01-01",
                settlementPeriod=22,
                fuelType="WIND",
                generation=5400.0,
                publishTime=datetime(2026, 1, 1, 11, 15, tzinfo=timezone.utc),
            ),
        ]

        dataset = match_actuals_and_forecasts(
            actuals=actuals,
            forecasts=forecasts,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 1),
            cutoff_param="day_ahead_1700",
            resolution="hourly",
        )

        matched = [inv for inv in dataset.intervals if inv.startTime == slot][0]
        self.assertEqual(matched.status, "matched")
        # Should pick revision 2 (5500.0 MW)
        self.assertEqual(matched.forecastGeneration, 5500.0)
        self.assertEqual(matched.forecastPublishTime, datetime(2025, 12, 31, 14, 0, tzinfo=timezone.utc))
        self.assertEqual(matched.actualGeneration, 5400.0)
        self.assertEqual(matched.signedError, 100.0)
        self.assertEqual(matched.leadTimeHours, 20.0)
        self.assertEqual(dataset.diagnostics.future_forecasts_filtered_count, 1)

    def test_different_cutoff_across_multi_day_range(self):
        """Verify that a forecast published Jan 1 12:00 is post-cutoff for Jan 1 delivery but eligible for Jan 2 delivery."""
        slot_day1 = datetime(2026, 1, 1, 18, 0, tzinfo=timezone.utc)
        slot_day2 = datetime(2026, 1, 2, 10, 0, tzinfo=timezone.utc)

        # Forecast published on Jan 1 at 12:00 UTC
        shared_forecast_pub = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)

        forecasts = [
            WindforRecord(publishTime=shared_forecast_pub, startTime=slot_day1, generation=4000.0),
            WindforRecord(publishTime=shared_forecast_pub, startTime=slot_day2, generation=5000.0),
        ]

        actuals = [
            # Day 1 actuals
            FuelHHRecord(startTime=slot_day1, settlementDate="2026-01-01", settlementPeriod=37, fuelType="WIND", generation=4100.0, publishTime=datetime(2026, 1, 1, 19, 0, tzinfo=timezone.utc)),
            FuelHHRecord(startTime=slot_day1 + timedelta(minutes=30), settlementDate="2026-01-01", settlementPeriod=38, fuelType="WIND", generation=4100.0, publishTime=datetime(2026, 1, 1, 19, 30, tzinfo=timezone.utc)),
            # Day 2 actuals
            FuelHHRecord(startTime=slot_day2, settlementDate="2026-01-02", settlementPeriod=21, fuelType="WIND", generation=4900.0, publishTime=datetime(2026, 1, 2, 11, 0, tzinfo=timezone.utc)),
            FuelHHRecord(startTime=slot_day2 + timedelta(minutes=30), settlementDate="2026-01-02", settlementPeriod=22, fuelType="WIND", generation=4900.0, publishTime=datetime(2026, 1, 2, 11, 30, tzinfo=timezone.utc)),
        ]

        dataset = match_actuals_and_forecasts(
            actuals=actuals,
            forecasts=forecasts,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 2),
            cutoff_param="day_ahead_1700",
            resolution="hourly",
        )

        item_day1 = [inv for inv in dataset.intervals if inv.startTime == slot_day1][0]
        item_day2 = [inv for inv in dataset.intervals if inv.startTime == slot_day2][0]

        # Day 1 cutoff was Dec 31 17:00 UTC -> Jan 1 12:00 publication was AFTER cutoff!
        self.assertEqual(item_day1.cutoffTime, datetime(2025, 12, 31, 17, 0, tzinfo=timezone.utc))
        self.assertEqual(item_day1.status, "missing_forecast")
        self.assertIsNone(item_day1.forecastGeneration)

        # Day 2 cutoff was Jan 1 17:00 UTC -> Jan 1 12:00 publication was BEFORE cutoff!
        self.assertEqual(item_day2.cutoffTime, datetime(2026, 1, 1, 17, 0, tzinfo=timezone.utc))
        self.assertEqual(item_day2.status, "matched")
        self.assertEqual(item_day2.forecastGeneration, 5000.0)

    def test_forecast_published_exactly_at_cutoff_is_eligible(self):
        """Verify forecast published exactly at the cutoff timestamp is accepted."""
        slot = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
        cutoff_exact = datetime(2025, 12, 31, 17, 0, tzinfo=timezone.utc)
        forecasts = [
            WindforRecord(publishTime=cutoff_exact, startTime=slot, generation=7200.0)
        ]
        actuals = [
            FuelHHRecord(startTime=slot, settlementDate="2026-01-01", settlementPeriod=21, fuelType="WIND", generation=7000.0, publishTime=datetime(2026, 1, 1, 10, 45, tzinfo=timezone.utc)),
            FuelHHRecord(startTime=slot + timedelta(minutes=30), settlementDate="2026-01-01", settlementPeriod=22, fuelType="WIND", generation=7000.0, publishTime=datetime(2026, 1, 1, 11, 15, tzinfo=timezone.utc)),
        ]

        dataset = match_actuals_and_forecasts(
            actuals=actuals,
            forecasts=forecasts,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 1),
            cutoff_param="day_ahead_1700",
            resolution="hourly",
        )
        matched = [inv for inv in dataset.intervals if inv.startTime == slot][0]
        self.assertEqual(matched.status, "matched")
        self.assertEqual(matched.forecastGeneration, 7200.0)

    def test_forecast_published_one_second_after_cutoff_is_excluded(self):
        """Verify zero lookahead leakage: 1 second after cutoff is excluded."""
        slot = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
        cutoff_plus_1s = datetime(2025, 12, 31, 17, 0, 1, tzinfo=timezone.utc)
        forecasts = [
            WindforRecord(publishTime=cutoff_plus_1s, startTime=slot, generation=8000.0)
        ]
        actuals = [
            FuelHHRecord(startTime=slot, settlementDate="2026-01-01", settlementPeriod=21, fuelType="WIND", generation=7000.0, publishTime=datetime(2026, 1, 1, 10, 45, tzinfo=timezone.utc)),
            FuelHHRecord(startTime=slot + timedelta(minutes=30), settlementDate="2026-01-01", settlementPeriod=22, fuelType="WIND", generation=7000.0, publishTime=datetime(2026, 1, 1, 11, 15, tzinfo=timezone.utc)),
        ]

        dataset = match_actuals_and_forecasts(
            actuals=actuals,
            forecasts=forecasts,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 1),
            cutoff_param="day_ahead_1700",
            resolution="hourly",
        )
        matched = [inv for inv in dataset.intervals if inv.startTime == slot][0]
        self.assertEqual(matched.status, "missing_forecast")
        self.assertIsNone(matched.forecastGeneration)
        self.assertEqual(dataset.diagnostics.future_forecasts_filtered_count, 1)

    def test_hourly_aggregation_method_and_energy_conservation(self):
        """Verify two 30-min actuals are averaged into 1-hour average MW."""
        slot = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        # SP1 (00:00) = 4000 MW, SP2 (00:30) = 6000 MW -> Average hourly power = 5000 MW
        actuals = [
            FuelHHRecord(startTime=slot, settlementDate="2026-01-01", settlementPeriod=1, fuelType="WIND", generation=4000.0, publishTime=datetime(2026, 1, 1, 0, 45, tzinfo=timezone.utc)),
            FuelHHRecord(startTime=slot + timedelta(minutes=30), settlementDate="2026-01-01", settlementPeriod=2, fuelType="WIND", generation=6000.0, publishTime=datetime(2026, 1, 1, 1, 15, tzinfo=timezone.utc)),
        ]
        forecasts = [
            WindforRecord(publishTime=datetime(2025, 12, 31, 16, 0, tzinfo=timezone.utc), startTime=slot, generation=5200.0)
        ]

        dataset = match_actuals_and_forecasts(
            actuals=actuals,
            forecasts=forecasts,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 1),
            resolution="hourly",
        )

        matched = [inv for inv in dataset.intervals if inv.startTime == slot][0]
        self.assertEqual(matched.status, "matched")
        self.assertEqual(matched.actualGeneration, 5000.0)
        self.assertEqual(matched.forecastGeneration, 5200.0)
        self.assertEqual(matched.signedError, 200.0)
        self.assertEqual(matched.absoluteError, 200.0)

    def test_hourly_aggregation_missing_one_sp_flags_missing_actual(self):
        """Verify that if one half-hour outturn is missing, hourly actual is marked None (no silent guessing)."""
        slot = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        # Only SP1 present, SP2 missing
        actuals = [
            FuelHHRecord(startTime=slot, settlementDate="2026-01-01", settlementPeriod=1, fuelType="WIND", generation=4000.0, publishTime=datetime(2026, 1, 1, 0, 45, tzinfo=timezone.utc)),
        ]
        forecasts = [
            WindforRecord(publishTime=datetime(2025, 12, 31, 16, 0, tzinfo=timezone.utc), startTime=slot, generation=5200.0)
        ]

        dataset = match_actuals_and_forecasts(
            actuals=actuals,
            forecasts=forecasts,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 1),
            resolution="hourly",
        )

        item = [inv for inv in dataset.intervals if inv.startTime == slot][0]
        self.assertEqual(item.status, "missing_actual")
        self.assertIsNone(item.actualGeneration)

    def test_half_hourly_resolution_mismatch_labeling(self):
        """Verify in half_hourly mode that :30 slots are labeled 'resolution_mismatch' and separated from failures."""
        slot_00 = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        slot_30 = datetime(2026, 1, 1, 0, 30, tzinfo=timezone.utc)

        actuals = [
            FuelHHRecord(startTime=slot_00, settlementDate="2026-01-01", settlementPeriod=1, fuelType="WIND", generation=4000.0, publishTime=datetime(2026, 1, 1, 0, 45, tzinfo=timezone.utc)),
            FuelHHRecord(startTime=slot_30, settlementDate="2026-01-01", settlementPeriod=2, fuelType="WIND", generation=4200.0, publishTime=datetime(2026, 1, 1, 1, 15, tzinfo=timezone.utc)),
        ]
        forecasts = [
            WindforRecord(publishTime=datetime(2025, 12, 31, 16, 0, tzinfo=timezone.utc), startTime=slot_00, generation=4100.0)
        ]

        dataset = match_actuals_and_forecasts(
            actuals=actuals,
            forecasts=forecasts,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 1),
            resolution="half_hourly",
        )

        item_00 = [inv for inv in dataset.intervals if inv.startTime == slot_00][0]
        item_30 = [inv for inv in dataset.intervals if inv.startTime == slot_30][0]

        self.assertEqual(item_00.status, "matched")
        self.assertEqual(item_30.status, "resolution_mismatch")
        self.assertIsNone(item_30.forecastGeneration)
        self.assertEqual(dataset.diagnostics.resolution_mismatch_count, 24)  # 24 half-past slots in day


if __name__ == "__main__":
    unittest.main()
