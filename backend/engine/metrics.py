"""Wind forecast accuracy metrics calculation engine.

Calculates standard forecast evaluation metrics:
- Mean Absolute Error (MAE) in MW
- Root Mean Squared Error (RMSE) in MW
- Signed Bias in MW (forecast - actual)
- Mean Absolute Percentage Error (MAPE) with explicit zero-actual handling
- Completeness percentage and coverage counts
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .cutoff import CUTOFF_METHODOLOGY_NOTES
from .matcher import MatchedDataset, MatchedInterval


@dataclass
class AccuracyMetrics:
    """Statistical accuracy metrics for matched wind forecast/actual pairs."""

    mae_mw: Optional[float]
    rmse_mw: Optional[float]
    signed_bias_mw: Optional[float]
    mape_pct: Optional[float]
    mape_excluded_zero_count: int
    matched_intervals_count: int
    expected_interval_count: int
    missing_forecast_count: int
    missing_actual_count: int
    data_completeness_pct: float
    selected_cutoff: str
    methodology: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize metrics to dictionary."""
        return {
            "mae_mw": round(self.mae_mw, 2) if self.mae_mw is not None else None,
            "rmse_mw": round(self.rmse_mw, 2) if self.rmse_mw is not None else None,
            "signed_bias_mw": round(self.signed_bias_mw, 2) if self.signed_bias_mw is not None else None,
            "mape_pct": round(self.mape_pct, 2) if self.mape_pct is not None else None,
            "mape_excluded_zero_count": self.mape_excluded_zero_count,
            "matched_intervals_count": self.matched_intervals_count,
            "expected_interval_count": self.expected_interval_count,
            "missing_forecast_count": self.missing_forecast_count,
            "missing_actual_count": self.missing_actual_count,
            "data_completeness_pct": round(self.data_completeness_pct, 2),
            "selected_cutoff": self.selected_cutoff,
            "methodology": self.methodology,
        }


def calculate_accuracy_metrics(dataset: MatchedDataset) -> AccuracyMetrics:
    """Compute MAE, RMSE, Bias, and MAPE across valid matched intervals in a dataset."""
    valid_pairs = dataset.valid_pairs
    expected_count = dataset.diagnostics.total_expected_intervals
    n = len(valid_pairs)

    completeness_pct = (n / expected_count * 100.0) if expected_count > 0 else 0.0

    if n == 0:
        return AccuracyMetrics(
            mae_mw=None,
            rmse_mw=None,
            signed_bias_mw=None,
            mape_pct=None,
            mape_excluded_zero_count=0,
            matched_intervals_count=0,
            expected_interval_count=expected_count,
            missing_forecast_count=dataset.diagnostics.missing_forecast_count,
            missing_actual_count=dataset.diagnostics.missing_actual_count,
            data_completeness_pct=completeness_pct,
            selected_cutoff=dataset.cutoff_canonical,
            methodology=f"{dataset.cutoff_description} {CUTOFF_METHODOLOGY_NOTES}",
        )

    signed_errors: List[float] = []
    abs_errors: List[float] = []
    sq_errors: List[float] = []
    pct_errors: List[float] = []
    excluded_zeros = 0

    for pair in valid_pairs:
        assert pair.actualGeneration is not None
        assert pair.forecastGeneration is not None

        act = pair.actualGeneration
        fc = pair.forecastGeneration

        err = fc - act
        abs_err = abs(err)
        sq_err = err * err

        signed_errors.append(err)
        abs_errors.append(abs_err)
        sq_errors.append(sq_err)

        if act != 0.0:
            pct_errors.append(abs_err / abs(act) * 100.0)
        else:
            excluded_zeros += 1

    mae = sum(abs_errors) / n
    rmse = math.sqrt(sum(sq_errors) / n)
    signed_bias = sum(signed_errors) / n
    mape = (sum(pct_errors) / len(pct_errors)) if pct_errors else None

    return AccuracyMetrics(
        mae_mw=mae,
        rmse_mw=rmse,
        signed_bias_mw=signed_bias,
        mape_pct=mape,
        mape_excluded_zero_count=excluded_zeros,
        matched_intervals_count=n,
        expected_interval_count=expected_count,
        missing_forecast_count=dataset.diagnostics.missing_forecast_count,
        missing_actual_count=dataset.diagnostics.missing_actual_count,
        data_completeness_pct=completeness_pct,
        selected_cutoff=dataset.cutoff_canonical,
        methodology=f"{dataset.cutoff_description} {CUTOFF_METHODOLOGY_NOTES}",
    )

