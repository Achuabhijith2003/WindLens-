"""Data models and validation structures for Elexon BMRS datasets."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


REQUIRED_FUELHH_FIELDS = [
    "startTime",
    "settlementDate",
    "settlementPeriod",
    "fuelType",
    "generation",
    "publishTime",
]


def parse_iso_datetime(value: Any) -> Optional[datetime]:
    """Parse an ISO 8601 string to a datetime object, handling 'Z' suffix."""
    if not value or not isinstance(value, str):
        return None
    try:
        # Replace Z with +00:00 for fromisoformat compatibility
        clean_val = value.replace("Z", "+00:00")
        return datetime.fromisoformat(clean_val)
    except (ValueError, TypeError):
        return None


@dataclass
class FuelHHRecord:
    """Represents a validated half-hourly generation outturn record."""

    startTime: datetime
    settlementDate: str
    settlementPeriod: int
    fuelType: str
    generation: float
    publishTime: datetime
    dataset: str = "FUELHH"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Tuple[Optional[FuelHHRecord], List[str]]:
        """Validate and parse a dictionary into a FuelHHRecord.

        Returns:
            A tuple of (record, missing_or_invalid_fields).
            If valid, record is not None and missing_or_invalid_fields is empty.
        """
        missing_or_invalid: List[str] = []

        for req_field in REQUIRED_FUELHH_FIELDS:
            if req_field not in data or data[req_field] is None:
                missing_or_invalid.append(req_field)

        start_dt = parse_iso_datetime(data.get("startTime"))
        if start_dt is None and "startTime" not in missing_or_invalid:
            missing_or_invalid.append("startTime_invalid_format")

        pub_dt = parse_iso_datetime(data.get("publishTime"))
        if pub_dt is None and "publishTime" not in missing_or_invalid:
            missing_or_invalid.append("publishTime_invalid_format")

        gen_val = data.get("generation")
        if gen_val is not None:
            try:
                gen_float = float(gen_val)
            except (ValueError, TypeError):
                missing_or_invalid.append("generation_not_numeric")
                gen_float = 0.0
        else:
            gen_float = 0.0

        sp_val = data.get("settlementPeriod")
        if sp_val is not None:
            try:
                sp_int = int(sp_val)
            except (ValueError, TypeError):
                missing_or_invalid.append("settlementPeriod_not_integer")
                sp_int = 0
        else:
            sp_int = 0

        fuel_type = str(data.get("fuelType", "")).strip()

        if missing_or_invalid:
            return None, missing_or_invalid

        record = cls(
            startTime=start_dt,  # type: ignore[arg-type]
            settlementDate=str(data.get("settlementDate", "")),
            settlementPeriod=sp_int,
            fuelType=fuel_type,
            generation=gen_float,
            publishTime=pub_dt,  # type: ignore[arg-type]
            dataset=str(data.get("dataset", "FUELHH")),
        )
        return record, []


@dataclass
class ExplorationReport:
    """Summary report detailing records retrieved, validation metrics, and time bounds."""

    query_publish_from: str
    query_publish_to: str
    total_records_received: int = 0
    non_wind_records_count: int = 0
    wind_records_count: int = 0
    valid_records_count: int = 0
    invalid_records_count: int = 0
    missing_fields_summary: Dict[str, int] = field(default_factory=dict)
    duplicate_start_times: List[str] = field(default_factory=list)
    duplicate_start_time_count: int = 0
    min_start_time: Optional[str] = None
    max_start_time: Optional[str] = None
    min_publish_time: Optional[str] = None
    max_publish_time: Optional[str] = None
    delivery_span_hours: Optional[float] = None
    generation_stats: Dict[str, float] = field(default_factory=dict)
    window_reports: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "query_publish_from": self.query_publish_from,
            "query_publish_to": self.query_publish_to,
            "total_records_received": self.total_records_received,
            "non_wind_records_count": self.non_wind_records_count,
            "wind_records_count": self.wind_records_count,
            "valid_records_count": self.valid_records_count,
            "invalid_records_count": self.invalid_records_count,
            "missing_fields_summary": self.missing_fields_summary,
            "duplicate_start_times": self.duplicate_start_times,
            "duplicate_start_time_count": self.duplicate_start_time_count,
            "min_start_time": self.min_start_time,
            "max_start_time": self.max_start_time,
            "min_publish_time": self.min_publish_time,
            "max_publish_time": self.max_publish_time,
            "delivery_span_hours": self.delivery_span_hours,
            "generation_stats": self.generation_stats,
            "window_reports": self.window_reports,
        }

    def summary_text(self) -> str:
        """Return formatted plain-text summary."""
        lines = [
            "============================================================",
            "          FUELHH EXPLORATION & VALIDATION REPORT           ",
            "============================================================",
            f"Publication Query Window:  {self.query_publish_from} to {self.query_publish_to}",
            f"Total Raw Records:         {self.total_records_received}",
            f"WIND Filtered Records:     {self.wind_records_count} (Non-WIND: {self.non_wind_records_count})",
            f"Valid WIND Records:        {self.valid_records_count}",
            f"Invalid/Malformed Records: {self.invalid_records_count}",
            "------------------------------------------------------------",
            f"Missing Fields Summary:    {self.missing_fields_summary or 'None'}",
            f"Duplicate startTimes:      {self.duplicate_start_time_count} distinct duplicated timestamps",
        ]
        if self.duplicate_start_times:
            sample_dups = self.duplicate_start_times[:5]
            lines.append(f"  Sample duplicate startTimes: {sample_dups}")
        lines.extend([
            "------------------------------------------------------------",
            f"Actual Delivery Range (startTime):",
            f"  Min startTime:           {self.min_start_time or 'N/A'}",
            f"  Max startTime:           {self.max_start_time or 'N/A'}",
            f"  Delivery Span (Hours):   {self.delivery_span_hours if self.delivery_span_hours is not None else 'N/A'}",
            f"Publication Time Range (publishTime):",
            f"  Min publishTime:         {self.min_publish_time or 'N/A'}",
            f"  Max publishTime:         {self.max_publish_time or 'N/A'}",
            "------------------------------------------------------------",
            f"Generation Output Stats (Calculated Dynamically in MW):",
            f"  Min Generation:          {self.generation_stats.get('min_mw', 'N/A')} MW",
            f"  Max Generation:          {self.generation_stats.get('max_mw', 'N/A')} MW",
            f"  Mean Generation:         {self.generation_stats.get('mean_mw', 'N/A')} MW",
            f"  Total Estimated Energy:  {self.generation_stats.get('total_mwh', 'N/A')} MWh (0.5h blocks)",
            "============================================================",
        ])
        return "\n".join(lines)

