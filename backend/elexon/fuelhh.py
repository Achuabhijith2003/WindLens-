"""FUELHH dataset exploration, validation, and windowed retrieval module."""

from __future__ import annotations

import logging
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from .client import ElexonClient, format_iso8601_utc
from .models import ExplorationReport, FuelHHRecord, parse_iso_datetime

logger = logging.getLogger(__name__)


def generate_date_windows(
    start: datetime,
    end: datetime,
    window_size: timedelta = timedelta(days=2),
) -> List[Tuple[datetime, datetime]]:
    """Partition a date-time interval into manageable consecutive chunks.

    Args:
        start: Beginning of overall time range.
        end: End of overall time range.
        window_size: Duration of each chunk (e.g. 2 days, 1 day).

    Returns:
        List of (window_start, window_end) tuples.
    """
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)

    if start >= end:
        raise ValueError(f"Start datetime ({start}) must be strictly earlier than end datetime ({end})")

    windows: List[Tuple[datetime, datetime]] = []
    current_start = start
    while current_start < end:
        current_end = min(current_start + window_size, end)
        windows.append((current_start, current_end))
        current_start = current_end
    return windows


def analyze_fuelhh_records(
    raw_records: List[Dict[str, Any]],
    query_from: datetime,
    query_to: datetime,
) -> Tuple[List[FuelHHRecord], ExplorationReport]:
    """Filter, validate, and analyze raw FUELHH records.

    Performs:
    1. Filter to fuelType == 'WIND' (case-insensitive).
    2. Validation of required fields.
    3. Duplicate startTime detection.
    4. Delivery bounds analysis (min/max startTime) vs Publication bounds (min/max publishTime).
    5. Missing field frequency aggregation.
    6. Generation statistics calculated dynamically from data.

    Returns:
        Tuple of (list_of_valid_FuelHHRecords, ExplorationReport).
    """
    report = ExplorationReport(
        query_publish_from=format_iso8601_utc(query_from),
        query_publish_to=format_iso8601_utc(query_to),
        total_records_received=len(raw_records),
    )

    valid_records: List[FuelHHRecord] = []
    missing_fields_counts: Counter[str] = Counter()
    start_time_occurrences: Counter[str] = Counter()

    for item in raw_records:
        fuel_type = str(item.get("fuelType", "")).strip().upper()
        if fuel_type != "WIND":
            report.non_wind_records_count += 1
            continue

        report.wind_records_count += 1
        record, errs = FuelHHRecord.from_dict(item)

        if errs:
            report.invalid_records_count += 1
            for err in errs:
                missing_fields_counts[err] += 1
        else:
            assert record is not None
            valid_records.append(record)
            start_iso = format_iso8601_utc(record.startTime)
            start_time_occurrences[start_iso] += 1

    report.valid_records_count = len(valid_records)
    report.missing_fields_summary = dict(missing_fields_counts)

    # Detect duplicate start times
    duplicate_start_times = [
        st for st, count in start_time_occurrences.items() if count > 1
    ]
    report.duplicate_start_times = sorted(duplicate_start_times)
    report.duplicate_start_time_count = len(duplicate_start_times)

    if valid_records:
        start_dts = [r.startTime for r in valid_records]
        publish_dts = [r.publishTime for r in valid_records]
        generations = [r.generation for r in valid_records]

        earliest_start = min(start_dts)
        latest_start = max(start_dts)
        earliest_pub = min(publish_dts)
        latest_pub = max(publish_dts)

        report.min_start_time = format_iso8601_utc(earliest_start)
        report.max_start_time = format_iso8601_utc(latest_start)
        report.min_publish_time = format_iso8601_utc(earliest_pub)
        report.max_publish_time = format_iso8601_utc(latest_pub)

        span_seconds = (latest_start - earliest_start).total_seconds()
        # Each settlement block is 30 mins (0.5 hours), span is diff between min and max start + 0.5h
        report.delivery_span_hours = round((span_seconds / 3600.0) + 0.5, 2)

        gen_min = round(float(min(generations)), 2)
        gen_max = round(float(max(generations)), 2)
        gen_mean = round(float(sum(generations) / len(generations)), 2)
        # 30-min settlement periods: 0.5 * MW gives MWh
        total_mwh = round(float(sum(generations)) * 0.5, 2)

        report.generation_stats = {
            "min_mw": gen_min,
            "max_mw": gen_max,
            "mean_mw": gen_mean,
            "total_mwh": total_mwh,
        }

    return valid_records, report


def fetch_fuelhh_windowed(
    client: ElexonClient,
    start: datetime,
    end: datetime,
    window_size: timedelta = timedelta(days=2),
    fuel_type: Optional[str] = "WIND",
    delay_seconds: float = 0.0,
) -> Tuple[List[FuelHHRecord], ExplorationReport]:
    """Retrieve actual FUELHH generation records in partitioned publication-time windows.

    Handles pagination across date chunks to stay within manageable payload sizes,
    records individual chunk diagnostics, and returns aggregated validated records.

    Note: The query parameters 'start' and 'end' correspond to the Elexon
    publication-time window (publishDateTimeFrom / publishDateTimeTo).
    The actual delivery time (startTime) is reported and validated separately.
    """
    windows = generate_date_windows(start, end, window_size)
    logger.info(
        "Partitioned publication range %s -> %s into %d windows of size %s",
        format_iso8601_utc(start),
        format_iso8601_utc(end),
        len(windows),
        window_size,
    )

    all_raw_records: List[Dict[str, Any]] = []
    window_reports: List[Dict[str, Any]] = []

    for idx, (win_start, win_end) in enumerate(windows, start=1):
        win_start_str = format_iso8601_utc(win_start)
        win_end_str = format_iso8601_utc(win_end)
        logger.info("Fetching window %d/%d: %s to %s", idx, len(windows), win_start_str, win_end_str)

        raw_chunk = client.fetch_fuelhh_stream(
            publish_from=win_start,
            publish_to=win_end,
            fuel_type=fuel_type,
        )
        all_raw_records.extend(raw_chunk)

        # Build sub-report for individual window
        _, chunk_report = analyze_fuelhh_records(raw_chunk, win_start, win_end)
        window_reports.append({
            "window_index": idx,
            "publish_from": win_start_str,
            "publish_to": win_end_str,
            "raw_count": len(raw_chunk),
            "valid_count": chunk_report.valid_records_count,
            "min_start_time": chunk_report.min_start_time,
            "max_start_time": chunk_report.max_start_time,
        })

        if delay_seconds > 0 and idx < len(windows):
            time.sleep(delay_seconds)

    # Global aggregation
    valid_records, global_report = analyze_fuelhh_records(all_raw_records, start, end)
    global_report.window_reports = window_reports

    return valid_records, global_report

