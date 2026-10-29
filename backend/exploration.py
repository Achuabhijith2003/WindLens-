"""WindLens Phase 1: Elexon BMRS Exploration CLI & Module.

Executes windowed queries against Elexon FUELHH and WINDFOR streams,
reports diagnostics (record counts, missing fields, duplicate startTimes,
min/max delivery start times), and documents publication vs delivery window dynamics.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from backend.elexon.client import (
    ElexonClient,
    ElexonAPIError,
    ElexonTimeoutError,
    ElexonHTTPStatusError,
    ElexonConnectionError,
    format_iso8601_utc,
)
from backend.elexon.fuelhh import (
    analyze_fuelhh_records,
    fetch_fuelhh_windowed,
    generate_date_windows,
)
from backend.elexon.models import ExplorationReport, FuelHHRecord
from backend.elexon.windfor import analyze_windfor_records

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(name)s: %(message)s",
)
logger = logging.getLogger("windlens.exploration")


def run_fuelhh_exploration(
    start_time: datetime,
    end_time: datetime,
    window_days: int = 2,
    fuel_type: str = "WIND",
    base_url: Optional[str] = None,
    client: Optional[ElexonClient] = None,
) -> Tuple[List[FuelHHRecord], ExplorationReport]:
    """Execute windowed retrieval and diagnostics for FUELHH.

    Args:
        start_time: Publication window start.
        end_time: Publication window end.
        window_days: Days per query chunk.
        fuel_type: Fuel type filter (default: "WIND").
        base_url: Optional custom Elexon API base URL.
        client: Optional pre-configured ElexonClient.

    Returns:
        Tuple of (valid_records, exploration_report).
    """
    logger.info("Initiating FUELHH exploration for publication range %s to %s", start_time, end_time)
    window_delta = timedelta(days=window_days)

    if client is not None:
        return fetch_fuelhh_windowed(
            client=client,
            start=start_time,
            end=end_time,
            window_size=window_delta,
            fuel_type=fuel_type,
        )

    client_kwargs = {}
    if base_url:
        client_kwargs["base_url"] = base_url

    with ElexonClient(**client_kwargs) as elexon_client:
        return fetch_fuelhh_windowed(
            client=elexon_client,
            start=start_time,
            end=end_time,
            window_size=window_delta,
            fuel_type=fuel_type,
        )


def run_windfor_investigation(
    start_time: datetime,
    end_time: datetime,
    base_url: Optional[str] = None,
    client: Optional[ElexonClient] = None,
) -> Any:
    """Execute investigation on WINDFOR historical publication stream."""
    logger.info("Initiating WINDFOR publication investigation for range %s to %s", start_time, end_time)

    def _fetch(cli: ElexonClient):
        raw = cli.fetch_windfor_stream(publish_from=start_time, publish_to=end_time)
        return analyze_windfor_records(raw, start_time, end_time)

    if client is not None:
        return _fetch(client)

    client_kwargs = {}
    if base_url:
        client_kwargs["base_url"] = base_url

    with ElexonClient(**client_kwargs) as elexon_client:
        return _fetch(elexon_client)


def main(args: Optional[List[str]] = None) -> int:
    """CLI entrypoint for exploration module."""
    parser = argparse.ArgumentParser(description="WindLens Phase 1 Exploration Module")
    parser.add_argument(
        "--start",
        type=str,
        default="2026-01-01T00:00:00Z",
        help="Publication range start (ISO 8601, default: 2026-01-01T00:00:00Z)",
    )
    parser.add_argument(
        "--end",
        type=str,
        default="2026-01-03T00:00:00Z",
        help="Publication range end (ISO 8601, default: 2026-01-03T00:00:00Z)",
    )
    parser.add_argument(
        "--window-days",
        type=int,
        default=2,
        help="Manageable window size in days (default: 2)",
    )
    parser.add_argument(
        "--fuel-type",
        type=str,
        default="WIND",
        help="Fuel type to filter (default: WIND)",
    )
    parser.add_argument(
        "--investigate-windfor",
        action="store_true",
        help="Also investigate WINDFOR stream publication records",
    )
    parser.add_argument(
        "--json-output",
        action="store_true",
        help="Output raw JSON report instead of formatted text",
    )

    parsed = parser.parse_args(args)

    try:
        start_dt = datetime.fromisoformat(parsed.start.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(parsed.end.replace("Z", "+00:00"))
    except ValueError as err:
        logger.error("Invalid ISO 8601 timestamp: %s", err)
        return 1

    try:
        valid_recs, report = run_fuelhh_exploration(
            start_time=start_dt,
            end_time=end_dt,
            window_days=parsed.window_days,
            fuel_type=parsed.fuel_type,
        )

        if parsed.json_output:
            print(json.dumps(report.to_dict(), indent=2))
        else:
            print(report.summary_text())

        if parsed.investigate_windfor:
            windfor_recs, windfor_report = run_windfor_investigation(start_dt, end_dt)
            print()
            print(windfor_report.summary_text())

        return 0

    except ElexonTimeoutError as exc:
        logger.error("Timeout communicating with Elexon API: %s", exc)
        return 2
    except ElexonHTTPStatusError as exc:
        logger.error("HTTP error from Elexon API [%s]: %s", exc.status_code, exc)
        return 3
    except ElexonConnectionError as exc:
        logger.error("Connection error reaching Elexon API: %s", exc)
        return 4
    except Exception as exc:
        logger.exception("Unexpected error during exploration: %s", exc)
        return 99


if __name__ == "__main__":
    sys.exit(main())

