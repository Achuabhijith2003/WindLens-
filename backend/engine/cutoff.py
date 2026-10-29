"""Decision cutoff resolution for wind generation forecast selection.

Supports:
1. Day-Ahead reference cutoffs (e.g. 'day_ahead_1700', 'day_ahead_1200'):
   Calculated independently for each delivery date D as (D - 1) at the specified UTC time.
   For multi-day delivery periods (e.g. all of January 2026), every delivery date receives
   its own separate cutoff (e.g. Jan 1 delivery cutoff is Dec 31 17:00 UTC; Jan 2 delivery
   cutoff is Jan 1 17:00 UTC). A single fixed cutoff is never used across the month.
   Explicit notice: This is an assumed analytical benchmark, not an official Elexon statutory deadline.
2. Lead-time / Gate closure cutoffs (e.g. 'gate_closure_1h', 'lead_4h'):
   Calculated per delivery slot as startTime - lead_time.
3. Absolute ISO 8601 timestamps (e.g. '2025-12-31T17:00:00Z'):
   Fixed cutoff applied uniformly across all intervals only when explicitly requested.
"""

from __future__ import annotations

import re
from datetime import datetime, time, timedelta, timezone
from typing import Callable, Optional, Tuple


DEFAULT_CUTOFF = "day_ahead_1700"

CUTOFF_METHODOLOGY_NOTES = (
    "Forecast Selection Methodology: "
    "For each delivery interval (startTime), forecasts published strictly at or before "
    "the applicable decision cutoff are evaluated. If multiple revisions exist, the latest publication "
    "(maximum publishTime <= cutoff) is chosen, ensuring zero lookahead bias. "
    "Under the default 'day_ahead_1700' rule, the cutoff is computed independently for each delivery date D "
    "as D-1 17:00:00 UTC (e.g. Jan 1 cutoff is Dec 31 17:00 UTC; Jan 2 cutoff is Jan 1 17:00 UTC). "
    "Note: This is an assumed analytical benchmark and not an official Elexon statutory deadline."
)


def get_cutoff_resolver(cutoff_param: Optional[str] = None) -> Tuple[Callable[[datetime], datetime], str, str]:
    """Parse a cutoff configuration parameter and return a resolver function.

    Args:
        cutoff_param: String describing the cutoff. If None or empty, defaults to 'day_ahead_1700'.

    Returns:
        Tuple of:
          - resolver: function taking interval_startTime (datetime) and returning cutoff_datetime (datetime in UTC).
          - canonical_name: normalized cutoff identifier.
          - description: human-readable explanation of the cutoff rule.

    Raises:
        ValueError: If cutoff_param format is unrecognized.
    """
    cutoff_str = (cutoff_param or DEFAULT_CUTOFF).strip().lower()

    # 1. Day-Ahead relative cutoffs: e.g. day_ahead_1700, d1_1700, day_ahead_1200
    da_match = re.match(r"^(?:day_ahead|d1)_(\d{2})(\d{2})$", cutoff_str)
    if da_match:
        hour, minute = int(da_match.group(1)), int(da_match.group(2))
        if hour > 23 or minute > 59:
            raise ValueError(f"Invalid time in cutoff parameter '{cutoff_param}': hour={hour}, minute={minute}")

        def da_resolver(delivery_start: datetime) -> datetime:
            # Normalize to UTC
            utc_start = delivery_start.astimezone(timezone.utc) if delivery_start.tzinfo else delivery_start.replace(tzinfo=timezone.utc)
            # D-1 date: calculated independently for each delivery date D
            d_minus_1 = utc_start.date() - timedelta(days=1)
            return datetime.combine(d_minus_1, time(hour, minute), tzinfo=timezone.utc)

        canonical = f"day_ahead_{hour:02d}{minute:02d}"
        desc = (
            f"Day-Ahead {hour:02d}:{minute:02d} UTC (D-1). "
            f"Calculated independently per delivery date D: evaluates forecasts published on or before {hour:02d}:{minute:02d} UTC on D-1."
        )
        return da_resolver, canonical, desc

    # 2. Gate Closure / Lead Time cutoffs: e.g. gate_closure_1h, lead_4h
    lead_match = re.match(r"^(?:gate_closure|lead)_(\d+(?:\.\d+)?)h?$", cutoff_str)
    if lead_match:
        lead_hours = float(lead_match.group(1))

        def lead_resolver(delivery_start: datetime) -> datetime:
            utc_start = delivery_start.astimezone(timezone.utc) if delivery_start.tzinfo else delivery_start.replace(tzinfo=timezone.utc)
            return utc_start - timedelta(hours=lead_hours)

        canonical = f"gate_closure_{lead_hours:g}h"
        desc = f"Gate Closure ({lead_hours:g}h lead time). Evaluates forecasts published at least {lead_hours:g} hours before delivery startTime."
        return lead_resolver, canonical, desc

    # 3. Absolute ISO 8601 cutoff timestamp: e.g. '2025-12-31T17:00:00Z'
    try:
        clean_iso = cutoff_param.replace("Z", "+00:00") if cutoff_param else ""
        abs_dt = datetime.fromisoformat(clean_iso)
        if abs_dt.tzinfo is None:
            abs_dt = abs_dt.replace(tzinfo=timezone.utc)
        else:
            abs_dt = abs_dt.astimezone(timezone.utc)

        def abs_resolver(_delivery_start: datetime) -> datetime:
            return abs_dt

        canonical = abs_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        desc = f"Absolute Cutoff: {canonical}. Evaluates forecasts published at or before this exact timestamp."
        return abs_resolver, canonical, desc
    except (ValueError, TypeError, AttributeError):
        pass

    raise ValueError(
        f"Unsupported cutoff format: '{cutoff_param}'. Supported formats include: "
        f"'day_ahead_1700' (default D-1 17:00 UTC), 'day_ahead_1200' (D-1 12:00 UTC), "
        f"'gate_closure_1h' (1 hour before delivery), 'lead_4h', or an explicit ISO 8601 timestamp (e.g. '2025-12-31T17:00:00Z')."
    )
