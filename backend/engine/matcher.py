"""Forecast and Actual generation matching engine.

Aligns actual generation (FUELHH) with forecasted generation (WINDFOR) by delivery startTime.
Applies configurable decision cutoffs, strictly prevents lookahead leakage,
preserves publication times and lead times, and detects data anomalies.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.elexon.client import format_iso8601_utc
from backend.elexon.models import FuelHHRecord
from backend.elexon.windfor import WindforRecord
from .cutoff import DEFAULT_CUTOFF, get_cutoff_resolver

logger = logging.getLogger(__name__)


def ensure_utc(dt: datetime) -> datetime:
    """Normalize datetime to timezone-aware UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@dataclass
class MatchedInterval:
    """Single delivery interval combining matched actual and forecast records."""

    startTime: datetime
    settlementDate: str
    settlementPeriod: Optional[int]
    cutoffTime: datetime
    actualGeneration: Optional[float] = None
    actualPublishTime: Optional[datetime] = None
    forecastGeneration: Optional[float] = None
    forecastPublishTime: Optional[datetime] = None
    leadTimeHours: Optional[float] = None
    signedError: Optional[float] = None       # forecast - actual
    absoluteError: Optional[float] = None     # |forecast - actual|
    percentageError: Optional[float] = None   # (|forecast - actual| / actual) * 100 if actual != 0
    status: str = "missing_both"               # 'matched', 'missing_forecast', 'missing_actual', 'missing_both'

    @property
    def is_valid_matched_pair(self) -> bool:
        return (
            self.status == "matched"
            and self.actualGeneration is not None
            and self.forecastGeneration is not None
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize interval to JSON-compatible dictionary."""
        return {
            "startTime": format_iso8601_utc(self.startTime),
            "settlementDate": self.settlementDate,
            "settlementPeriod": self.settlementPeriod,
            "cutoffTime": format_iso8601_utc(self.cutoffTime),
            "actualGeneration": round(self.actualGeneration, 2) if self.actualGeneration is not None else None,
            "actualPublishTime": format_iso8601_utc(self.actualPublishTime) if self.actualPublishTime else None,
            "forecastGeneration": round(self.forecastGeneration, 2) if self.forecastGeneration is not None else None,
            "forecastPublishTime": format_iso8601_utc(self.forecastPublishTime) if self.forecastPublishTime else None,
            "leadTimeHours": round(self.leadTimeHours, 2) if self.leadTimeHours is not None else None,
            "signedError": round(self.signedError, 2) if self.signedError is not None else None,
            "absoluteError": round(self.absoluteError, 2) if self.absoluteError is not None else None,
            "percentageError": round(self.percentageError, 2) if self.percentageError is not None else None,
            "status": self.status,
        }


@dataclass
class MatchingDiagnostics:
    """Diagnostics and quality checks for the matching process."""

    total_expected_intervals: int = 0
    matched_intervals_count: int = 0
    missing_actual_count: int = 0
    missing_forecast_count: int = 0
    missing_both_count: int = 0
    duplicate_actual_records: int = 0
    conflicting_actual_records: int = 0
    duplicate_forecast_records: int = 0
    conflicting_forecast_records: int = 0
    future_forecasts_filtered_count: int = 0
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_expected_intervals": self.total_expected_intervals,
            "matched_intervals_count": self.matched_intervals_count,
            "missing_actual_count": self.missing_actual_count,
            "missing_forecast_count": self.missing_forecast_count,
            "missing_both_count": self.missing_both_count,
            "duplicate_actual_records": self.duplicate_actual_records,
            "conflicting_actual_records": self.conflicting_actual_records,
            "duplicate_forecast_records": self.duplicate_forecast_records,
            "conflicting_forecast_records": self.conflicting_forecast_records,
            "future_forecasts_filtered_count": self.future_forecasts_filtered_count,
            "warnings": self.warnings,
        }


@dataclass
class MatchedDataset:
    """Complete collection of matched intervals across a delivery period."""

    start_date: str
    end_date: str
    cutoff_canonical: str
    cutoff_description: str
    intervals: List[MatchedInterval]
    diagnostics: MatchingDiagnostics

    @property
    def valid_pairs(self) -> List[MatchedInterval]:
        return [interval for interval in self.intervals if interval.is_valid_matched_pair]


def generate_expected_intervals(
    start_date: date,
    end_date: date,
    step_minutes: int = 30,
) -> List[datetime]:
    """Generate regular UTC delivery intervals across the date range."""
    if start_date > end_date:
        raise ValueError(f"start_date ({start_date}) cannot be after end_date ({end_date})")

    start_dt = datetime.combine(start_date, time(0, 0), tzinfo=timezone.utc)
    # End of the final day: 23:59:59
    end_dt = datetime.combine(end_date + timedelta(days=1), time(0, 0), tzinfo=timezone.utc)

    intervals: List[datetime] = []
    curr = start_dt
    delta = timedelta(minutes=step_minutes)
    while curr < end_dt:
        intervals.append(curr)
        curr += delta
    return intervals


def match_actuals_and_forecasts(
    actuals: List[FuelHHRecord],
    forecasts: List[WindforRecord],
    start_date: date,
    end_date: date,
    cutoff_param: Optional[str] = DEFAULT_CUTOFF,
    step_minutes: int = 30,
) -> MatchedDataset:
    """Align FUELHH actuals and WINDFOR forecasts by delivery startTime under a cutoff rule.

    Rules applied:
    1. Timestamps normalized to timezone-aware UTC.
    2. Cutoff resolved per delivery slot.
    3. Exclude any forecast where publishTime > cutoff (zero lookahead).
    4. For eligible forecasts (publishTime <= cutoff), select the latest (maximum publishTime).
    5. Detect and log duplicates/conflicts.
    6. No zero-filling of missing intervals.
    """
    cutoff_resolver, cutoff_name, cutoff_desc = get_cutoff_resolver(cutoff_param)
    expected_times = generate_expected_intervals(start_date, end_date, step_minutes=step_minutes)

    diagnostics = MatchingDiagnostics(total_expected_intervals=len(expected_times))

    # 1. Index actuals by delivery startTime
    actual_by_start: Dict[datetime, List[FuelHHRecord]] = defaultdict(list)
    for act in actuals:
        utc_start = ensure_utc(act.startTime)
        actual_by_start[utc_start].append(act)

    # Validate actual duplicates / conflicts
    deduped_actual: Dict[datetime, FuelHHRecord] = {}
    for st, act_list in actual_by_start.items():
        if len(act_list) > 1:
            diagnostics.duplicate_actual_records += (len(act_list) - 1)
            # Check for conflicting generation values
            unique_gens = {r.generation for r in act_list}
            if len(unique_gens) > 1:
                diagnostics.conflicting_actual_records += 1
                msg = f"Conflicting FUELHH generation outturn at {format_iso8601_utc(st)}: values={unique_gens}"
                diagnostics.warnings.append(msg)
                logger.warning(msg)
            # Use the latest published actual record
            deduped_actual[st] = max(act_list, key=lambda r: ensure_utc(r.publishTime))
        else:
            deduped_actual[st] = act_list[0]

    # 2. Index forecasts by delivery startTime
    forecast_by_start: Dict[datetime, List[WindforRecord]] = defaultdict(list)
    for fc in forecasts:
        utc_start = ensure_utc(fc.startTime)
        forecast_by_start[utc_start].append(fc)

    # 3. Match across all expected intervals
    intervals: List[MatchedInterval] = []

    for slot in expected_times:
        slot_cutoff = cutoff_resolver(slot)
        date_str = slot.strftime("%Y-%m-%d")

        # Settlement period calculation (1-48 for half-hourly)
        period_idx = int((slot.hour * 60 + slot.minute) / step_minutes) + 1

        actual_rec = deduped_actual.get(slot)
        forecast_candidates = forecast_by_start.get(slot, [])

        # Filter forecasts to those published strictly at or before cutoff
        eligible_forecasts: List[WindforRecord] = []
        for fc in forecast_candidates:
            pub_utc = ensure_utc(fc.publishTime)
            if pub_utc <= slot_cutoff:
                eligible_forecasts.append(fc)
            else:
                diagnostics.future_forecasts_filtered_count += 1

        selected_fc: Optional[WindforRecord] = None
        if eligible_forecasts:
            # Check for duplicate forecast publications for the same run
            pub_counts = defaultdict(list)
            for ef in eligible_forecasts:
                pub_counts[ensure_utc(ef.publishTime)].append(ef)
            for pub_t, f_list in pub_counts.items():
                if len(f_list) > 1:
                    diagnostics.duplicate_forecast_records += (len(f_list) - 1)
                    if len({f.generation for f in f_list}) > 1:
                        diagnostics.conflicting_forecast_records += 1
                        diagnostics.warnings.append(
                            f"Conflicting WINDFOR forecast for start={format_iso8601_utc(slot)} pub={format_iso8601_utc(pub_t)}"
                        )

            # Select latest eligible forecast
            selected_fc = max(eligible_forecasts, key=lambda f: ensure_utc(f.publishTime))

        # Determine interval status
        act_gen = actual_rec.generation if actual_rec else None
        act_pub = ensure_utc(actual_rec.publishTime) if actual_rec else None
        fc_gen = selected_fc.generation if selected_fc else None
        fc_pub = ensure_utc(selected_fc.publishTime) if selected_fc else None

        lead_hours: Optional[float] = None
        if selected_fc and fc_pub:
            lead_hours = (slot - fc_pub).total_seconds() / 3600.0

        if act_gen is not None and fc_gen is not None:
            status = "matched"
            signed_err = fc_gen - act_gen
            abs_err = abs(signed_err)
            pct_err = (abs_err / act_gen * 100.0) if act_gen != 0.0 else None
            diagnostics.matched_intervals_count += 1
        elif act_gen is not None and fc_gen is None:
            status = "missing_forecast"
            signed_err = None
            abs_err = None
            pct_err = None
            diagnostics.missing_forecast_count += 1
        elif act_gen is None and fc_gen is not None:
            status = "missing_actual"
            signed_err = None
            abs_err = None
            pct_err = None
            diagnostics.missing_actual_count += 1
        else:
            status = "missing_both"
            signed_err = None
            abs_err = None
            pct_err = None
            diagnostics.missing_both_count += 1

        matched_item = MatchedInterval(
            startTime=slot,
            settlementDate=date_str,
            settlementPeriod=period_idx if step_minutes == 30 else None,
            cutoffTime=slot_cutoff,
            actualGeneration=act_gen,
            actualPublishTime=act_pub,
            forecastGeneration=fc_gen,
            forecastPublishTime=fc_pub,
            leadTimeHours=lead_hours,
            signedError=signed_err,
            absoluteError=abs_err,
            percentageError=pct_err,
            status=status,
        )
        intervals.append(matched_item)

    return MatchedDataset(
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        cutoff_canonical=cutoff_name,
        cutoff_description=cutoff_desc,
        intervals=intervals,
        diagnostics=diagnostics,
    )

