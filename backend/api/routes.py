"""FastAPI router implementation for WindLens endpoints."""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from backend.engine.cutoff import DEFAULT_CUTOFF, get_cutoff_resolver
from backend.services.data_service import DataService
from .schemas import (
    AccuracyResponse,
    HealthResponse,
    OverviewResponse,
    TimeseriesResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Default singleton service for live requests; can be overridden via dependency injection
_data_service: Optional[DataService] = None


def get_data_service() -> DataService:
    global _data_service
    if _data_service is None:
        _data_service = DataService()
    return _data_service


def set_data_service(service: DataService) -> None:
    """Override singleton service (used in testing)."""
    global _data_service
    _data_service = service


def parse_date(date_str: str, param_name: str) -> date:
    """Validate and parse YYYY-MM-DD date parameter."""
    try:
        return datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid date format for '{param_name}': '{date_str}'. Expected format YYYY-MM-DD.",
        )


def validate_cutoff(cutoff_str: Optional[str]) -> str:
    """Validate cutoff parameter string."""
    cutoff = cutoff_str or DEFAULT_CUTOFF
    try:
        get_cutoff_resolver(cutoff)
        return cutoff
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Health check endpoint confirming service status and version."""
    return HealthResponse(
        status="ok",
        app="WindLens",
        version="0.2.0",
        timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )


@router.get("/overview", response_model=OverviewResponse)
def get_daily_overview(
    date: str = Query("2026-01-01", description="Target delivery date (YYYY-MM-DD)"),
    cutoff: Optional[str] = Query(DEFAULT_CUTOFF, description="Decision cutoff configuration"),
    service: DataService = Depends(get_data_service),
) -> OverviewResponse:
    """Retrieve daily summary, generation distribution, and high-level accuracy metrics."""
    target_date = parse_date(date, "date")
    valid_cutoff = validate_cutoff(cutoff)

    try:
        overview_dict = service.get_overview(target_date, cutoff_param=valid_cutoff)
        return OverviewResponse(**overview_dict)
    except Exception as exc:
        logger.exception("Error in GET /api/overview: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to generate overview: {exc}")


@router.get("/timeseries", response_model=TimeseriesResponse)
def get_daily_timeseries(
    date: str = Query("2026-01-01", description="Target delivery date (YYYY-MM-DD)"),
    cutoff: Optional[str] = Query(DEFAULT_CUTOFF, description="Decision cutoff configuration"),
    service: DataService = Depends(get_data_service),
) -> TimeseriesResponse:
    """Retrieve half-hourly timeseries of actuals, selected forecasts, errors, and lead times."""
    target_date = parse_date(date, "date")
    valid_cutoff = validate_cutoff(cutoff)

    try:
        ts_dict = service.get_timeseries(target_date, cutoff_param=valid_cutoff)
        return TimeseriesResponse(**ts_dict)
    except Exception as exc:
        logger.exception("Error in GET /api/timeseries: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to generate timeseries: {exc}")


@router.get("/accuracy", response_model=AccuracyResponse)
def get_accuracy_range(
    from_date: str = Query("2026-01-01", alias="from", description="Delivery start date (YYYY-MM-DD)"),
    to_date: str = Query("2026-01-31", alias="to", description="Delivery end date (YYYY-MM-DD)"),
    cutoff: Optional[str] = Query(DEFAULT_CUTOFF, description="Decision cutoff configuration"),
    service: DataService = Depends(get_data_service),
) -> AccuracyResponse:
    """Evaluate aggregate and daily accuracy metrics across a multi-day delivery range."""
    start_dt = parse_date(from_date, "from")
    end_dt = parse_date(to_date, "to")

    if end_dt < start_dt:
        raise HTTPException(
            status_code=400,
            detail=f"Parameter 'to' ({to_date}) must be on or after 'from' ({from_date}).",
        )

    valid_cutoff = validate_cutoff(cutoff)

    try:
        acc_dict = service.get_accuracy_range(start_dt, end_dt, cutoff_param=valid_cutoff)
        return AccuracyResponse(**acc_dict)
    except Exception as exc:
        logger.exception("Error in GET /api/accuracy: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to calculate accuracy: {exc}")

