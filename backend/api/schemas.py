"""Pydantic request and response schemas for WindLens API."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str = Field(..., example="ok")
    app: str = Field(..., example="WindLens")
    version: str = Field(..., example="0.2.0")
    timestamp: str = Field(..., example="2026-01-01T00:00:00Z")


class AccuracyMetricsModel(BaseModel):
    """Core statistical forecast accuracy metrics schema."""

    mae_mw: Optional[float] = Field(None, description="Mean Absolute Error in MW")
    rmse_mw: Optional[float] = Field(None, description="Root Mean Squared Error in MW")
    signed_bias_mw: Optional[float] = Field(None, description="Signed bias (forecast - actual) in MW")
    mape_pct: Optional[float] = Field(None, description="Mean Absolute Percentage Error (%)")
    mape_excluded_zero_count: int = Field(0, description="Count of actual=0 intervals excluded from MAPE")
    matched_intervals_count: int = Field(..., description="Number of valid matched delivery intervals")
    expected_interval_count: int = Field(..., description="Expected intervals in the requested delivery range")
    missing_forecast_count: int = Field(0, description="Intervals with missing or post-cutoff forecast")
    missing_actual_count: int = Field(0, description="Intervals with missing actual generation outturn")
    data_completeness_pct: float = Field(..., description="Percentage of expected intervals matched")
    selected_cutoff: str = Field(..., description="Decision cutoff configuration applied")
    methodology: str = Field(..., description="Explicit documentation of methodology & cutoff assumptions")


class DiagnosticsModel(BaseModel):
    """Diagnostic data and quality anomaly tracking schema."""

    total_expected_intervals: int
    matched_intervals_count: int
    missing_actual_count: int
    missing_forecast_count: int
    missing_both_count: int
    duplicate_actual_records: int
    conflicting_actual_records: int
    duplicate_forecast_records: int
    conflicting_forecast_records: int
    future_forecasts_filtered_count: int
    warnings: List[str]


class SummaryStatsModel(BaseModel):
    """Generation outturn/forecast distribution statistics."""

    count: int
    min_mw: Optional[float] = None
    max_mw: Optional[float] = None
    mean_mw: Optional[float] = None
    total_mwh: Optional[float] = None


class OverviewResponse(BaseModel):
    """Response schema for GET /api/overview."""

    date: str
    cutoff: str
    cutoffDescription: str
    metrics: AccuracyMetricsModel
    actualSummary: SummaryStatsModel
    forecastSummary: SummaryStatsModel
    diagnostics: DiagnosticsModel
    methodology: str


class TimeseriesIntervalModel(BaseModel):
    """Single delivery interval entry in timeseries response."""

    startTime: str
    settlementDate: str
    settlementPeriod: Optional[int] = None
    cutoffTime: str
    actualGeneration: Optional[float] = None
    actualPublishTime: Optional[str] = None
    forecastGeneration: Optional[float] = None
    forecastPublishTime: Optional[str] = None
    leadTimeHours: Optional[float] = None
    signedError: Optional[float] = None
    absoluteError: Optional[float] = None
    percentageError: Optional[float] = None
    status: str


class TimeseriesResponse(BaseModel):
    """Response schema for GET /api/timeseries."""

    date: str
    cutoff: str
    cutoffDescription: str
    metrics: AccuracyMetricsModel
    diagnostics: DiagnosticsModel
    intervals: List[TimeseriesIntervalModel]


class DailyAccuracyModel(BaseModel):
    """Daily summary element in multi-day accuracy response."""

    date: str
    metrics: AccuracyMetricsModel
    matchedCount: int
    expectedCount: int


class AccuracyResponse(BaseModel):
    """Response schema for GET /api/accuracy."""

    fromDate: str
    toDate: str
    cutoff: str
    cutoffDescription: str
    metrics: AccuracyMetricsModel
    diagnostics: DiagnosticsModel
    dailyBreakdown: List[DailyAccuracyModel]

