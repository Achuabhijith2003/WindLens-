"""Data service coordinating live Elexon retrieval, disk/memory caching, matching, and metrics."""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.elexon.client import ElexonClient, format_iso8601_utc
from backend.elexon.fuelhh import fetch_fuelhh_windowed
from backend.elexon.models import FuelHHRecord, parse_iso_datetime
from backend.elexon.windfor import WindforRecord
from backend.engine.cutoff import DEFAULT_CUTOFF
from backend.engine.matcher import MatchedDataset, match_actuals_and_forecasts
from backend.engine.metrics import AccuracyMetrics, calculate_accuracy_metrics

logger = logging.getLogger(__name__)

_ROOT_CACHE = Path(__file__).resolve().parent.parent.parent / "data" / "cache"
CACHE_DIR = _ROOT_CACHE if _ROOT_CACHE.exists() else Path("data/cache")


class DataService:
    """Service providing matched actual and forecast datasets with disk & in-memory caching."""

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
            try:
                self.cache_dir.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                logger.warning("Could not create cache directory (read-only filesystem): %s", exc)

        # In-memory storage for cached records
        self._actuals_cache: Dict[str, FuelHHRecord] = {}     # keyed by startTime ISO
        self._forecasts_cache: Dict[Tuple[str, str], WindforRecord] = {} # keyed by (startTime ISO, publishTime ISO)

        if self.enable_disk_cache:
            self._load_disk_cache()

    def _load_disk_cache(self) -> None:
        """Load persisted cache entries from disk if available."""
        fuelhh_path = self.cache_dir / "fuelhh_cache.json"
        windfor_path = self.cache_dir / "windfor_cache.json"

        if fuelhh_path.exists():
            try:
                with open(fuelhh_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for item in data:
                    rec, errs = FuelHHRecord.from_dict(item)
                    if rec and not errs:
                        st = format_iso8601_utc(rec.startTime)
                        self._actuals_cache[st] = rec
                logger.info("Loaded %d FUELHH records from disk cache", len(self._actuals_cache))
            except Exception as exc:
                logger.warning("Could not read FUELHH disk cache: %s", exc)

        if windfor_path.exists():
            try:
                with open(windfor_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for item in data:
                    rec, errs = WindforRecord.from_dict(item)
                    if rec and not errs:
                        st = format_iso8601_utc(rec.startTime)
                        pt = format_iso8601_utc(rec.publishTime)
                        self._forecasts_cache[(st, pt)] = rec
                logger.info("Loaded %d WINDFOR records from disk cache", len(self._forecasts_cache))
            except Exception as exc:
                logger.warning("Could not read WINDFOR disk cache: %s", exc)

    def _save_disk_cache(self) -> None:
        """Persist in-memory records to disk cache safely."""
        if not self.enable_disk_cache:
            return

        fuelhh_path = self.cache_dir / "fuelhh_cache.json"
        windfor_path = self.cache_dir / "windfor_cache.json"

        try:
            actuals_data = [
                {
                    "dataset": r.dataset,
                    "publishTime": format_iso8601_utc(r.publishTime),
                    "startTime": format_iso8601_utc(r.startTime),
                    "settlementDate": r.settlementDate,
                    "settlementPeriod": r.settlementPeriod,
                    "fuelType": r.fuelType,
                    "generation": r.generation,
                }
                for r in self._actuals_cache.values()
            ]
            with open(fuelhh_path, "w", encoding="utf-8") as f:
                json.dump(actuals_data, f, indent=2)

            forecasts_data = [
                {
                    "dataset": r.dataset,
                    "publishTime": format_iso8601_utc(r.publishTime),
                    "startTime": format_iso8601_utc(r.startTime),
                    "settlementDate": r.settlementDate,
                    "settlementPeriod": r.settlementPeriod,
                    "generation": r.generation,
                }
                for r in self._forecasts_cache.values()
            ]
            with open(windfor_path, "w", encoding="utf-8") as f:
                json.dump(forecasts_data, f, indent=2)
        except Exception as exc:
            logger.warning("Failed to save disk cache: %s", exc)

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
        requested_dates = {start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)}
        cached_dates = {
            rec.startTime.date() for rec in self._actuals_cache.values()
            if start_date <= rec.startTime.date() <= end_date
        }
        if requested_dates.issubset(cached_dates):
            return [
                rec for rec in self._actuals_cache.values()
                if start_date <= rec.startTime.date() <= end_date
            ]

        missing_dates = sorted(requested_dates - cached_dates)
        fetch_start = min(missing_dates)
        fetch_end = max(missing_dates)

        # FUELHH publication time: query publish window from fetch_start to fetch_end + 2 days
        pub_from = datetime.combine(fetch_start, datetime.min.time(), tzinfo=timezone.utc)
        pub_to = datetime.combine(fetch_end + timedelta(days=2), datetime.min.time(), tzinfo=timezone.utc)

        logger.info("Fetching FUELHH stream for delivery %s to %s (publish: %s -> %s)", fetch_start, fetch_end, pub_from, pub_to)
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

        self._save_disk_cache()

        return [
            rec for rec in self._actuals_cache.values()
            if start_date <= rec.startTime.date() <= end_date
        ]

    def fetch_forecasts_for_delivery_dates(self, start_date: date, end_date: date) -> List[WindforRecord]:
        """Retrieve WINDFOR forecast records covering the specified delivery period."""
        requested_dates = {start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)}
        cached_dates = {
            fc.startTime.date() for fc in self._forecasts_cache.values()
            if start_date <= fc.startTime.date() <= end_date
        }
        if requested_dates.issubset(cached_dates):
            return [
                fc for fc in self._forecasts_cache.values()
                if start_date <= fc.startTime.date() <= end_date
            ]

        missing_dates = sorted(requested_dates - cached_dates)
        fetch_start = min(missing_dates)
        fetch_end = max(missing_dates)

        # Include necessary lookback window: forecasts for early January 2026 delivery
        # were published in late December 2025.
        lookback_days = 7
        pub_from = datetime.combine(fetch_start - timedelta(days=lookback_days), datetime.min.time(), tzinfo=timezone.utc)
        pub_to = datetime.combine(fetch_end + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)

        logger.info("Fetching WINDFOR stream for delivery %s to %s (publish: %s -> %s)", fetch_start, fetch_end, pub_from, pub_to)

        curr_from = pub_from
        all_raw_forecasts: List[Dict[str, Any]] = []
        while curr_from < pub_to:
            curr_to = min(curr_from + timedelta(days=2), pub_to)
            chunk = self.client.fetch_windfor_stream(publish_from=curr_from, publish_to=curr_to)
            all_raw_forecasts.extend(chunk)
            curr_from = curr_to

        for item in all_raw_forecasts:
            fc_rec, errs = WindforRecord.from_dict(item)
            if not errs and fc_rec:
                st = format_iso8601_utc(fc_rec.startTime)
                pt = format_iso8601_utc(fc_rec.publishTime)
                self._forecasts_cache[(st, pt)] = fc_rec

        self._save_disk_cache()

        return [
            fc for fc in self._forecasts_cache.values()
            if start_date <= fc.startTime.date() <= end_date
        ]

    def get_matched_dataset(
        self,
        start_date: date,
        end_date: date,
        cutoff_param: Optional[str] = DEFAULT_CUTOFF,
        resolution: str = "hourly",
    ) -> MatchedDataset:
        """Fetch records and generate the matched dataset under the chosen cutoff and resolution."""
        actuals = self.fetch_actuals_for_delivery_dates(start_date, end_date)
        forecasts = self.fetch_forecasts_for_delivery_dates(start_date, end_date)

        return match_actuals_and_forecasts(
            actuals=actuals,
            forecasts=forecasts,
            start_date=start_date,
            end_date=end_date,
            cutoff_param=cutoff_param,
            resolution=resolution,
        )

    def get_overview(
        self,
        target_date: date,
        cutoff_param: Optional[str] = DEFAULT_CUTOFF,
        resolution: str = "hourly",
    ) -> Dict[str, Any]:
        """Generate high-level daily overview and summary metrics for a specific delivery date."""
        dataset = self.get_matched_dataset(target_date, target_date, cutoff_param=cutoff_param, resolution=resolution)
        metrics = calculate_accuracy_metrics(dataset)

        actual_gens = [
            m.actualGeneration for m in dataset.intervals if m.actualGeneration is not None
        ]
        forecast_gens = [
            m.forecastGeneration for m in dataset.intervals if m.forecastGeneration is not None
        ]

        mult = 1.0 if resolution == "hourly" else 0.5
        actual_summary = {
            "count": len(actual_gens),
            "min_mw": round(min(actual_gens), 2) if actual_gens else None,
            "max_mw": round(max(actual_gens), 2) if actual_gens else None,
            "mean_mw": round(sum(actual_gens) / len(actual_gens), 2) if actual_gens else None,
            "total_mwh": round(sum(actual_gens) * mult, 2) if actual_gens else None,
        }

        forecast_summary = {
            "count": len(forecast_gens),
            "min_mw": round(min(forecast_gens), 2) if forecast_gens else None,
            "max_mw": round(max(forecast_gens), 2) if forecast_gens else None,
            "mean_mw": round(sum(forecast_gens) / len(forecast_gens), 2) if forecast_gens else None,
        }

        return {
            "date": target_date.isoformat(),
            "resolution": dataset.resolution,
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
        resolution: str = "hourly",
    ) -> Dict[str, Any]:
        """Generate timeseries of actuals, forecasts, errors, and lead times."""
        dataset = self.get_matched_dataset(target_date, target_date, cutoff_param=cutoff_param, resolution=resolution)
        metrics = calculate_accuracy_metrics(dataset)

        return {
            "date": target_date.isoformat(),
            "resolution": dataset.resolution,
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
        resolution: str = "hourly",
    ) -> Dict[str, Any]:
        """Evaluate accuracy metrics across a multi-day range (e.g. all of January 2026)."""
        dataset = self.get_matched_dataset(start_date, end_date, cutoff_param=cutoff_param, resolution=resolution)
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
                resolution=dataset.resolution,
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
            "resolution": dataset.resolution,
            "cutoff": dataset.cutoff_canonical,
            "cutoffDescription": dataset.cutoff_description,
            "metrics": overall_metrics.to_dict(),
            "diagnostics": dataset.diagnostics.to_dict(),
            "dailyBreakdown": daily_breakdown,
        }
