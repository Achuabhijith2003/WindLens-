"""WINDFOR dataset exploration and analysis module.

Investigates historical publication records, forecast horizon characteristics,
and why publication-time filtering differs fundamentally from delivery-time windowing.
"""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .client import format_iso8601_utc
from .models import parse_iso_datetime

logger = logging.getLogger(__name__)


@dataclass
class WindforRecord:
    """Represents a validated wind generation forecast record."""

    publishTime: datetime
    startTime: datetime
    generation: float
    settlementDate: Optional[str] = None
    settlementPeriod: Optional[int] = None
    dataset: str = "WINDFOR"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Tuple[Optional[WindforRecord], List[str]]:
        """Validate and parse a raw WINDFOR record dictionary."""
        missing_or_invalid: List[str] = []

        pub_dt = parse_iso_datetime(data.get("publishTime"))
        if pub_dt is None:
            missing_or_invalid.append("publishTime")

        start_dt = parse_iso_datetime(data.get("startTime"))
        if start_dt is None:
            missing_or_invalid.append("startTime")

        gen_val = data.get("generation")
        if gen_val is not None:
            try:
                gen_float = float(gen_val)
            except (ValueError, TypeError):
                missing_or_invalid.append("generation_not_numeric")
                gen_float = 0.0
        else:
            missing_or_invalid.append("generation")
            gen_float = 0.0

        if missing_or_invalid:
            return None, missing_or_invalid

        sp_val = data.get("settlementPeriod")
        sp_int = int(sp_val) if sp_val is not None and str(sp_val).isdigit() else None

        return cls(
            publishTime=pub_dt,  # type: ignore[arg-type]
            startTime=start_dt,  # type: ignore[arg-type]
            generation=gen_float,
            settlementDate=data.get("settlementDate"),
            settlementPeriod=sp_int,
            dataset=str(data.get("dataset", "WINDFOR")),
        ), []


@dataclass
class WindforAnalysisReport:
    """Report detailing WINDFOR publication records vs delivery periods."""

    query_publish_from: str
    query_publish_to: str
    total_records: int = 0
    valid_records_count: int = 0
    invalid_records_count: int = 0
    unique_publish_runs: int = 0
    unique_delivery_start_times: int = 0
    min_publish_time: Optional[str] = None
    max_publish_time: Optional[str] = None
    min_delivery_start_time: Optional[str] = None
    max_delivery_start_time: Optional[str] = None
    min_lead_time_hours: Optional[float] = None
    max_lead_time_hours: Optional[float] = None
    mean_revisions_per_delivery_time: float = 0.0
    max_revisions_for_single_delivery_time: int = 0
    delivery_extends_beyond_query_window: bool = False
    delivery_precedes_query_window: bool = False
    findings_and_uncertainties: List[str] = field(default_factory=list)

    def summary_text(self) -> str:
        """Format report into plain text summary."""
        lines = [
            "============================================================",
            "          WINDFOR FORECAST INVESTIGATION REPORT             ",
            "============================================================",
            f"Publication Query Window:      {self.query_publish_from} to {self.query_publish_to}",
            f"Total Forecast Records:        {self.total_records}",
            f"Valid Records:                 {self.valid_records_count}",
            f"Unique Forecast Runs (pubs):   {self.unique_publish_runs}",
            f"Unique Delivery Times (starts):{self.unique_delivery_start_times}",
            "------------------------------------------------------------",
            f"Publication Range (publishTime):",
            f"  Earliest Publish Time:       {self.min_publish_time or 'N/A'}",
            f"  Latest Publish Time:         {self.max_publish_time or 'N/A'}",
            f"Delivery Range (startTime):",
            f"  Earliest Delivery Start:     {self.min_delivery_start_time or 'N/A'}",
            f"  Latest Delivery Start:       {self.max_delivery_start_time or 'N/A'}",
            "------------------------------------------------------------",
            f"Forecast Horizon & Revision Metrics:",
            f"  Min Lead Time (startTime - publishTime): {self.min_lead_time_hours} hours",
            f"  Max Lead Time (startTime - publishTime): {self.max_lead_time_hours} hours",
            f"  Mean Revisions per Delivery Slot:        {self.mean_revisions_per_delivery_time}",
            f"  Max Revisions for Single Delivery Slot:  {self.max_revisions_for_single_delivery_time}",
            "------------------------------------------------------------",
            "Key Findings & Structural Observations:",
        ]
        for idx, finding in enumerate(self.findings_and_uncertainties, start=1):
            lines.append(f"  {idx}. {finding}")
        lines.append("============================================================")
        return "\n".join(lines)


def analyze_windfor_records(
    raw_records: List[Dict[str, Any]],
    query_from: datetime,
    query_to: datetime,
) -> Tuple[List[WindforRecord], WindforAnalysisReport]:
    """Analyze WINDFOR records to uncover forecast horizons, publication patterns, and window mismatches."""
    report = WindforAnalysisReport(
        query_publish_from=format_iso8601_utc(query_from),
        query_publish_to=format_iso8601_utc(query_to),
        total_records=len(raw_records),
    )

    valid_records: List[WindforRecord] = []
    publish_runs: Counter[str] = Counter()
    delivery_times: defaultdict[str, List[WindforRecord]] = defaultdict(list)
    lead_times_hours: List[float] = []

    for item in raw_records:
        rec, errs = WindforRecord.from_dict(item)
        if errs:
            report.invalid_records_count += 1
            continue
        assert rec is not None
        valid_records.append(rec)
        pub_iso = format_iso8601_utc(rec.publishTime)
        start_iso = format_iso8601_utc(rec.startTime)
        publish_runs[pub_iso] += 1
        delivery_times[start_iso].append(rec)

        lead_h = (rec.startTime - rec.publishTime).total_seconds() / 3600.0
        lead_times_hours.append(lead_h)

    report.valid_records_count = len(valid_records)
    report.unique_publish_runs = len(publish_runs)
    report.unique_delivery_start_times = len(delivery_times)

    findings: List[str] = []

    if valid_records:
        min_pub = min(r.publishTime for r in valid_records)
        max_pub = max(r.publishTime for r in valid_records)
        min_start = min(r.startTime for r in valid_records)
        max_start = max(r.startTime for r in valid_records)

        report.min_publish_time = format_iso8601_utc(min_pub)
        report.max_publish_time = format_iso8601_utc(max_pub)
        report.min_delivery_start_time = format_iso8601_utc(min_start)
        report.max_delivery_start_time = format_iso8601_utc(max_start)

        report.min_lead_time_hours = round(min(lead_times_hours), 2)
        report.max_lead_time_hours = round(max(lead_times_hours), 2)

        rev_counts = [len(recs) for recs in delivery_times.values()]
        report.mean_revisions_per_delivery_time = round(sum(rev_counts) / len(rev_counts), 2)
        report.max_revisions_for_single_delivery_time = max(rev_counts)

        # Check if delivery range exceeds publication range
        if query_to.tzinfo is None:
            q_to = query_to.replace(tzinfo=timezone.utc)
        else:
            q_to = query_to.astimezone(timezone.utc)

        if query_from.tzinfo is None:
            q_from = query_from.replace(tzinfo=timezone.utc)
        else:
            q_from = query_from.astimezone(timezone.utc)

        if max_start > q_to:
            report.delivery_extends_beyond_query_window = True
            findings.append(
                f"Delivery horizon extends beyond publication window: latest delivery {report.max_delivery_start_time} "
                f"> publication window end {report.query_publish_to} by {round((max_start - q_to).total_seconds() / 3600.0, 1)} hours."
            )

        if min_start < q_from:
            report.delivery_precedes_query_window = True
            findings.append(
                f"Delivery start precedes publication window: earliest delivery {report.min_delivery_start_time} "
                f"< publication window start {report.query_publish_from}."
            )

    findings.append(
        "Publication-time filtering does NOT guarantee a complete set of forecasts for a delivery period: "
        "Forecasts for the first delivery periods of January 2026 (e.g. 2026-01-01 00:00) are generated and "
        "published in late December 2025 (e.g. Day-Ahead run on 2025-12-31). Querying only publishDateTime >= 2026-01-01 "
        "omits these prior day-ahead forecasts."
    )
    findings.append(
        "Multiple forecast revisions per delivery period: NESO updates wind forecasts up to 8 times daily. "
        "Consequently, querying by publication time produces multiple overlapping forecast values for each delivery interval."
    )
    findings.append(
        "Horizon selection ambiguity: In Phase 2, the pipeline must define a deterministic forecast selection strategy "
        "(e.g., 'latest forecast before gate closure', 'day-ahead forecast at D-1 17:00 UTC', or 'multi-horizon evolution matrix')."
    )

    report.findings_and_uncertainties = findings
    return valid_records, report

