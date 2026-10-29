"""Tests for wind generation forecast accuracy metrics calculations.

Verifies:
1. Mean Absolute Error (MAE) in MW.
2. Root Mean Squared Error (RMSE) in MW.
3. Signed Bias in MW (forecast - actual).
4. Mean Absolute Percentage Error (MAPE) with nonzero actual filtering.
5. Excluded zero actual count tracking.
6. Empty datasets handling (zero division protection).
7. Data completeness percentage and resolution-specific metrics.
8. Separation of resolution mismatch from missing forecast failures.
"""

import math
import unittest
from datetime import datetime, timezone

from backend.engine.matcher import MatchedDataset, MatchedInterval, MatchingDiagnostics
from backend.engine.metrics import calculate_accuracy_metrics


class TestAccuracyMetrics(unittest.TestCase):
    """Test accuracy metric formulas and edge cases."""

    def test_standard_metrics_calculation(self):
        """Verify standard MAE, RMSE, Bias, and MAPE on deterministic values."""
        # Pair 1: Actual = 100 MW, Forecast = 110 MW -> err = +10, abs = 10, pct = 10%
        # Pair 2: Actual = 200 MW, Forecast = 180 MW -> err = -20, abs = 20, pct = 10%
        # Pair 3: Actual = 300 MW, Forecast = 330 MW -> err = +30, abs = 30, pct = 10%
        # Pair 4: Actual = 400 MW, Forecast = 400 MW -> err =   0, abs =  0, pct =  0%
        # Total pairs N = 4
        # MAE = (10 + 20 + 30 + 0) / 4 = 15.0 MW
        # RMSE = sqrt((100 + 400 + 900 + 0) / 4) = sqrt(1400 / 4) = sqrt(350) = 18.708...
        # Signed Bias = (10 - 20 + 30 + 0) / 4 = +5.0 MW (over-forecasting)
        # MAPE = (10% + 10% + 10% + 0%) / 4 = 7.5%
        now = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        intervals = [
            MatchedInterval(
                startTime=now,
                settlementDate="2026-01-01",
                settlementPeriod=1,
                cutoffTime=now,
                actualGeneration=100.0,
                forecastGeneration=110.0,
                status="matched",
                signedError=10.0,
                absoluteError=10.0,
                percentageError=10.0,
            ),
            MatchedInterval(
                startTime=now,
                settlementDate="2026-01-01",
                settlementPeriod=2,
                cutoffTime=now,
                actualGeneration=200.0,
                forecastGeneration=180.0,
                status="matched",
                signedError=-20.0,
                absoluteError=20.0,
                percentageError=10.0,
            ),
            MatchedInterval(
                startTime=now,
                settlementDate="2026-01-01",
                settlementPeriod=3,
                cutoffTime=now,
                actualGeneration=300.0,
                forecastGeneration=330.0,
                status="matched",
                signedError=30.0,
                absoluteError=30.0,
                percentageError=10.0,
            ),
            MatchedInterval(
                startTime=now,
                settlementDate="2026-01-01",
                settlementPeriod=4,
                cutoffTime=now,
                actualGeneration=400.0,
                forecastGeneration=400.0,
                status="matched",
                signedError=0.0,
                absoluteError=0.0,
                percentageError=0.0,
            ),
        ]

        dataset = MatchedDataset(
            start_date="2026-01-01",
            end_date="2026-01-01",
            cutoff_canonical="day_ahead_1700",
            cutoff_description="Day-Ahead 17:00 UTC",
            intervals=intervals,
            diagnostics=MatchingDiagnostics(total_expected_intervals=8, matched_intervals_count=4),
            resolution="hourly",
        )

        metrics = calculate_accuracy_metrics(dataset)

        self.assertAlmostEqual(metrics.mae_mw, 15.0, places=2)
        self.assertAlmostEqual(metrics.rmse_mw, math.sqrt(350.0), places=2)
        self.assertAlmostEqual(metrics.signed_bias_mw, 5.0, places=2)
        self.assertAlmostEqual(metrics.mape_pct, 7.5, places=2)
        self.assertEqual(metrics.mape_excluded_zero_count, 0)
        self.assertEqual(metrics.matched_intervals_count, 4)
        self.assertEqual(metrics.expected_interval_count, 8)
        self.assertEqual(metrics.data_completeness_pct, 50.0)
        self.assertEqual(metrics.resolution, "hourly")

    def test_mape_excludes_zero_actual_generation(self):
        """Verify intervals with actual=0 are excluded from MAPE and counted."""
        now = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        intervals = [
            # Actual = 0, Forecast = 50 -> division by zero avoided!
            MatchedInterval(
                startTime=now,
                settlementDate="2026-01-01",
                settlementPeriod=1,
                cutoffTime=now,
                actualGeneration=0.0,
                forecastGeneration=50.0,
                status="matched",
                signedError=50.0,
                absoluteError=50.0,
            ),
            # Actual = 100, Forecast = 120 -> 20%
            MatchedInterval(
                startTime=now,
                settlementDate="2026-01-01",
                settlementPeriod=2,
                cutoffTime=now,
                actualGeneration=100.0,
                forecastGeneration=120.0,
                status="matched",
                signedError=20.0,
                absoluteError=20.0,
            ),
        ]

        dataset = MatchedDataset(
            start_date="2026-01-01",
            end_date="2026-01-01",
            cutoff_canonical="day_ahead_1700",
            cutoff_description="Day-Ahead 17:00 UTC",
            intervals=intervals,
            diagnostics=MatchingDiagnostics(total_expected_intervals=2, matched_intervals_count=2),
            resolution="hourly",
        )

        metrics = calculate_accuracy_metrics(dataset)

        self.assertEqual(metrics.matched_intervals_count, 2)
        self.assertEqual(metrics.mape_excluded_zero_count, 1)
        # MAPE should be exactly 20.0% (from the single non-zero interval)
        self.assertAlmostEqual(metrics.mape_pct, 20.0, places=2)
        # MAE includes both intervals: (50 + 20) / 2 = 35.0 MW
        self.assertAlmostEqual(metrics.mae_mw, 35.0, places=2)

    def test_all_actuals_zero_yields_none_mape(self):
        """Verify MAPE is None when all actual values are zero."""
        now = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        intervals = [
            MatchedInterval(
                startTime=now,
                settlementDate="2026-01-01",
                settlementPeriod=1,
                cutoffTime=now,
                actualGeneration=0.0,
                forecastGeneration=10.0,
                status="matched",
                signedError=10.0,
                absoluteError=10.0,
            )
        ]
        dataset = MatchedDataset(
            start_date="2026-01-01",
            end_date="2026-01-01",
            cutoff_canonical="day_ahead_1700",
            cutoff_description="Day-Ahead 17:00 UTC",
            intervals=intervals,
            diagnostics=MatchingDiagnostics(total_expected_intervals=1, matched_intervals_count=1),
            resolution="hourly",
        )

        metrics = calculate_accuracy_metrics(dataset)
        self.assertIsNone(metrics.mape_pct)
        self.assertEqual(metrics.mape_excluded_zero_count, 1)
        self.assertEqual(metrics.mae_mw, 10.0)

    def test_empty_dataset_handling(self):
        """Verify empty dataset does not crash and returns None for metrics."""
        dataset = MatchedDataset(
            start_date="2026-01-01",
            end_date="2026-01-01",
            cutoff_canonical="day_ahead_1700",
            cutoff_description="Day-Ahead 17:00 UTC",
            intervals=[],
            diagnostics=MatchingDiagnostics(total_expected_intervals=48, matched_intervals_count=0),
            resolution="half_hourly",
        )

        metrics = calculate_accuracy_metrics(dataset)
        self.assertIsNone(metrics.mae_mw)
        self.assertIsNone(metrics.rmse_mw)
        self.assertIsNone(metrics.signed_bias_mw)
        self.assertIsNone(metrics.mape_pct)
        self.assertEqual(metrics.matched_intervals_count, 0)
        self.assertEqual(metrics.data_completeness_pct, 0.0)
        self.assertEqual(metrics.resolution, "half_hourly")

    def test_resolution_mismatch_counted_separately_from_missing_forecast(self):
        """Verify resolution mismatch is tracked in metrics separately from pipeline failures."""
        dataset = MatchedDataset(
            start_date="2026-01-01",
            end_date="2026-01-01",
            cutoff_canonical="day_ahead_1700",
            cutoff_description="Day-Ahead 17:00 UTC",
            intervals=[],
            diagnostics=MatchingDiagnostics(
                total_expected_intervals=48,
                matched_intervals_count=20,
                missing_forecast_count=4,
                resolution_mismatch_count=24,
            ),
            resolution="half_hourly",
        )

        metrics = calculate_accuracy_metrics(dataset)
        self.assertEqual(metrics.resolution_mismatch_count, 24)
        self.assertEqual(metrics.missing_forecast_count, 4)


if __name__ == "__main__":
    unittest.main()
