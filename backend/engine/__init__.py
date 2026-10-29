"""WindLens engine package for cutoff resolution, matching, and accuracy metrics."""

from .cutoff import DEFAULT_CUTOFF, CUTOFF_METHODOLOGY_NOTES, get_cutoff_resolver
from .matcher import (
    MatchedInterval,
    MatchingDiagnostics,
    MatchedDataset,
    match_actuals_and_forecasts,
    generate_expected_intervals,
)
from .metrics import AccuracyMetrics, calculate_accuracy_metrics

__all__ = [
    "DEFAULT_CUTOFF",
    "CUTOFF_METHODOLOGY_NOTES",
    "get_cutoff_resolver",
    "MatchedInterval",
    "MatchingDiagnostics",
    "MatchedDataset",
    "match_actuals_and_forecasts",
    "generate_expected_intervals",
    "AccuracyMetrics",
    "calculate_accuracy_metrics",
]

