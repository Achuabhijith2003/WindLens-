"""Data service coordinating live Elexon retrieval, disk/memory caching, matching, and metrics."""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.elexon.client import ElexonClient, format_iso8601_utc
from backend.elexon.fuelhh import fetch_fuelhh_windowed
from backend.elexon.models import FuelHHRecord
from backend.elexon.windfor import WindforRecord
from backend.engine.cutoff import DEFAULT_CUTOFF
from backend.engine.matcher import MatchedDataset, match_actuals_and_forecasts
from backend.engine.metrics import AccuracyMetrics, calculate_accuracy_metrics

logger = logging.getLogger(__name__)

CACHE_DIR = Path("data/cache")


class DataService:
    """Service providing matched actual and forecast datasets with caching."""

    def __init__(
        self,
        client: Optional[ElexonClient] = None,
        cache_dir: Optional[Path] = None,
        enable_disk_cache: bool = True,
    ):
        self.client = client or ElexonClient()
        self.cache_dir = cache_dir or CACHE_DIR
        self.enable_disk_cache = enable_disk_cache
        if self.enable_disk_cache:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

        # In-memory storage for cached records
        self._actuals_cache: Dict[str, FuelHHRecord] = {}     # keyed by startTime ISO
        self._forecasts_cache: Dict[Tuple[str, str], WindforRecord] = {} # keyed by (startTime ISO, publishTime ISO)

    def load_records_into_cache(
        self,
        actuals: Optional[List[FuelHHRecord]] = None,
        forecasts: Optional[List[WindforRecord]] = None,
    ) -> None:
        """Inject in-memory records directly into cache (useful for testing and offline operation)."""
        if actuals:
            for act in actuals:
                st = format_iso8601_utc(act.startTime)
                self._actuals_cache[st] = act
        if forecasts:
            for fc in forecasts:
                st = format_iso8601_utc(fc.startTime)
                pt = format_iso8601_utc(fc.publishTime)
                self._forecasts_cache[(st, pt)] = fc

    def clear_cache(self) -> None:
        """Clear memory cache."""
        self._actuals_cache.clear()
        self._forecasts_cache.clear()

    def fetch_actuals_for_delivery_dates(self, start_date: date, end_date: date) -> List[FuelHHRecord]:
        """Retrieve FUELHH actual generation records covering the specified delivery period."""
        # Check if already in cache
        cached_actuals = [
            rec for rec in self._actuals_cache.values()
            if start_date <= rec.startTime.date() <= end_date
        ]
        # In a full day there are 48 half-hour slots. If cached records cover the range, return them.
        days_count = (end_date - start_date).days + 1
        expected_slots = days_count * 48
        if len(cached_actuals) >= expected_slots:
            return cached_actuals

        # FUELHH publication time: settlement outturns publish shortly after period end.
        # Query publish window from start_date 00:00 UTC to end_date + 2 days to capture final outturn runs.
        pub_from = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
        pub_to = datetime.combine(end_date + timedelta(days=2), datetime.min.time(), tzinfo=timezone.utc)

        logger.info("Fetching FUELHH stream for delivery %s to %s (publish: %s -> %s)", start_date, end_date, pub_from, pub_to)
        valid_recs, _ = fetch_fuelhh_windowed(
            client=self.client,
            start=pub_from,
            end=pub_to,
            window_size=timedelta(days=2),
            fuel_type="WIND",
        )

        for rec in valid_recs:
            st = format_iso8601_utc(rec.startTime)
            self._actuals_cache[st] = rec

        return [
            rec for rec in self._actuals_cache.values()
            if start_date <= rec.startTime.date() <= end_date
        ]

    def fetch_forecasts_for_delivery_dates(self, start_date: date, end_date: date) -> List[WindforRecord]:
        """Retrieve WINDFOR forecast records covering the specified delivery period."""
        cached_forecasts = [
            fc for fc in self._forecasts_cache.values()
            if start_date <= fc.startTime.date() <= end_date
        ]
        if cached_forecasts:
            return cached_forecasts

        # Include necessary lookback window: forecasts for early January 2026 delivery
        # were published in late December 2025.
        lookback_days = 7
        pub_from = datetime.combine(start_date - timedelta(days=lookback_days), datetime.min.time(), tzinfo=timezone.utc)
        pub_to = datetime.combine(end_date + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)

        logger.info("Fetching WINDFOR stream for delivery %s to %s (publish: %s -> %s)", start_date, end_date, pub_from, pub_to)
        
        # Partition WINDFOR publication queries into 2-day windows
        curr_from = pub_from
        all_raw_forecasts: List[Dict[str, Any]] = []
        while curr_from < pub_to:
            curr_to = min(curr_from + timedelta(days=2), pub_to)
            chunk = self.client.fetch_windfor_stream(publish_from=curr_from, publish_to=curr_to)
            all_raw_forecasts.extend(chunk)
            curr_from = curr_to

        valid_fc_list: List[WindforRecord] = []
        for item in all_raw_forecasts:
            fc_rec, errs = WindforRecord.from_dict(item)
            if not errs and fc_rec:
                st = format_iso8601_utc(fc_rec.startTime)
                pt = format_iso8601_utc(fc_rec.publishTime)
                self._forecasts_cache[(st, pt)] = fc_rec
                valid_fc_list.append(fc_rec)

        return [
            fc for fc in self._forecasts_cache.values()
            if start_date <= fc.startTime.date() <= end_date
        ]

    def get_matched_dataset(
        self,
        start_date: date,
        end_date: date,
        cutoff_param: Optional[str] = DEFAULT_CUTOFF,
        step_minutes: int = 30,
    ) -> MatchedDataset:
        """Fetch records and generate the matched dataset under the chosen cutoff."""
        actuals = self.fetch_actuals_for_delivery_dates(start_date, end_date)
        forecasts = self.fetch_forecasts_for_delivery_dates(start_date, end_date)

        return match_actuals_and_forecasts(
            actuals=actuals,
            forecasts=forecasts,
            start_date=start_date,
            end_date=end_date,
            cutoff_param=cutoff_param,
            step_minutes=step_minutes,
        )

    def get_overview(
        self,
        target_date: date,
        cutoff_param: Optional[str] = DEFAULT_CUTOFF,
    ) -> Dict[str, Any]:
        """Generate high-level daily overview and summary metrics for a specific delivery date."""
        dataset = self.get_matched_dataset(target_date, target_date, cutoff_param=cutoff_param)
        metrics = calculate_accuracy_metrics(dataset)

        actual_gens = [
            m.actualGeneration for m in dataset.intervals if m.actualGeneration is not None
        ]
        forecast_gens = [
            m.forecastGeneration for m in dataset.intervals if m.forecastGeneration is not None
        ]

        actual_summary = {
            "count": len(actual_gens),
            "min_mw": round(min(actual_gens), 2) if actual_gens else None,
            "max_mw": round(max(actual_gens), 2) if actual_gens else None,
            "mean_mw": round(sum(actual_gens) / len(actual_gens), 2) if actual_gens else None,
            "total_mwh": round(sum(actual_gens) * 0.5, 2) if actual_gens else None,
        }

        forecast_summary = {
            "count": len(forecast_gens),
            "min_mw": round(min(forecast_gens), 2) if forecast_gens else None,
            "max_mw": round(max(forecast_gens), 2) if forecast_gens else None,
            "mean_mw": round(sum(forecast_gens) / len(forecast_gens), 2) if forecast_gens else None,
        }

        return {
            "date": target_date.isoformat(),
            "cutoff": dataset.cutoff_canonical,
            "cutoffDescription": dataset.cutoff_description,
            "metrics": metrics.to_dict(),
            "actualSummary": actual_summary,
            "forecastSummary": forecast_summary,
            "diagnostics": dataset.diagnostics.to_dict(),
            "methodology": metrics.methodology,
        }

    def get_timeseries(
        self,
        target_date: date,
        cutoff_param: Optional[str] = DEFAULT_CUTOFF,
    ) -> Dict[str, Any]:
        """Generate half-hourly timeseries of actuals, forecasts, errors, and lead times."""
        dataset = self.get_matched_dataset(target_date, target_date, cutoff_param=cutoff_param)
        metrics = calculate_accuracy_metrics(dataset)

        return {
            "date": target_date.isoformat(),
            "cutoff": dataset.cutoff_canonical,
            "cutoffDescription": dataset.cutoff_description,
            "metrics": metrics.to_dict(),
            "diagnostics": dataset.diagnostics.to_dict(),
            "intervals": [interval.to_dict() for interval in dataset.intervals],
        }

    def get_accuracy_range(
        self,
        start_date: date,
        end_date: date,
        cutoff_param: Optional[str] = DEFAULT_CUTOFF,
    ) -> Dict[str, Any]:
        """Evaluate accuracy metrics across a multi-day range (e.g. all of January 2026)."""
        dataset = self.get_matched_dataset(start_date, end_date, cutoff_param=cutoff_param)
        overall_metrics = calculate_accuracy_metrics(dataset)

        # Compute per-day breakdown
        daily_breakdown: List[Dict[str, Any]] = []
        curr = start_date
        while curr <= end_date:
            curr_str = curr.isoformat()
            day_intervals = [
                inv for inv in dataset.intervals if inv.settlementDate == curr_str
            ]
            day_valid = [inv for inv in day_intervals if inv.is_valid_matched_pair]
            day_expected = len(day_intervals)

            day_dataset = MatchedDataset(
                start_date=curr_str,
                end_date=curr_str,
                cutoff_canonical=dataset.cutoff_canonical,
                cutoff_description=dataset.cutoff_description,
                intervals=day_intervals,
                diagnostics=dataset.diagnostics,
            )
            day_metrics = calculate_accuracy_metrics(day_dataset)

            daily_breakdown.append({
                "date": curr_str,
                "metrics": day_metrics.to_dict(),
                "matchedCount": len(day_valid),
                "expectedCount": day_expected,
            })
            curr += timedelta(days=1)

        return {
            "fromDate": start_date.isoformat(),
            "toDate": end_date.isoformat(),
            "cutoff": dataset.cutoff_canonical,
            "cutoffDescription": dataset.cutoff_description,
            "metrics": overall_metrics.to_dict(),
            "diagnostics": dataset.diagnostics.to_dict(),
            "dailyBreakdown": daily_breakdown,
        }
