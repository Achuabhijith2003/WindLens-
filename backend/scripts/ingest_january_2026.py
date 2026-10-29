"""Full January 2026 ingestion, verification, and evaluation script for WindLens."""

import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.engine.metrics import calculate_accuracy_metrics
from backend.services.data_service import DataService


def ingest_and_evaluate_january():
    print("=" * 70)
    print("WINDLENS: FULL JANUARY 2026 INGESTION & ACCURACY EVALUATION")
    print("=" * 70)

    service = DataService(enable_disk_cache=True)
    start_date = date(2026, 1, 1)
    end_date = date(2026, 1, 31)

    print(f"\n[1/4] Ingesting FUELHH actual generation ({start_date} to {end_date})...")
    actuals = service.fetch_actuals_for_delivery_dates(start_date, end_date)
    print(f"      Total actual records retrieved & cached: {len(actuals)}")
    if actuals:
        earliest_act = min(a.startTime for a in actuals)
        latest_act = max(a.startTime for a in actuals)
        print(f"      Earliest delivery startTime: {earliest_act}")
        print(f"      Latest delivery startTime:   {latest_act}")

    print(f"\n[2/4] Ingesting WINDFOR forecast revisions ({start_date} to {end_date})...")
    forecasts = service.fetch_forecasts_for_delivery_dates(start_date, end_date)
    print(f"      Total forecast records retrieved & cached: {len(forecasts)}")
    if forecasts:
        earliest_fc_pub = min(f.publishTime for f in forecasts)
        latest_fc_pub = max(f.publishTime for f in forecasts)
        earliest_fc_start = min(f.startTime for f in forecasts)
        latest_fc_start = max(f.startTime for f in forecasts)
        print(f"      Earliest publication time:   {earliest_fc_pub}")
        print(f"      Latest publication time:     {latest_fc_pub}")
        print(f"      Earliest delivery startTime: {earliest_fc_start}")
        print(f"      Latest delivery startTime:   {latest_fc_start}")

    print("\n[3/4] Running Month-Long Matching Engine (Hourly resolution, day_ahead_1700)...")
    dataset_hourly = service.get_matched_dataset(
        start_date=start_date,
        end_date=end_date,
        cutoff_param="day_ahead_1700",
        resolution="hourly",
    )
    diag_h = dataset_hourly.diagnostics
    metrics_h = calculate_accuracy_metrics(dataset_hourly)

    print(f"      Total expected hourly intervals: {diag_h.total_expected_intervals} (31 days * 24h = 744)")
    print(f"      Matched hourly intervals:        {diag_h.matched_intervals_count}")
    print(f"      Missing forecast intervals:      {diag_h.missing_forecast_count}")
    print(f"      Missing actual intervals:        {diag_h.missing_actual_count}")
    print(f"      Post-cutoff revisions filtered:  {diag_h.future_forecasts_filtered_count}")

    print("\n      Full-Month Accuracy Metrics (Hourly):")
    print(f"      - MAE:          {metrics_h.mae_mw:.2f} MW" if metrics_h.mae_mw is not None else "      - MAE: N/A")
    print(f"      - RMSE:         {metrics_h.rmse_mw:.2f} MW" if metrics_h.rmse_mw is not None else "      - RMSE: N/A")
    print(f"      - Signed Bias:  {metrics_h.signed_bias_mw:.2f} MW" if metrics_h.signed_bias_mw is not None else "      - Signed Bias: N/A")
    print(f"      - MAPE:         {metrics_h.mape_pct:.2f}% (Excluded zero actuals: {metrics_h.mape_excluded_zero_count})" if metrics_h.mape_pct is not None else "      - MAPE: N/A")
    print(f"      - Completeness: {metrics_h.data_completeness_pct:.2f}%")

    print("\n[4/4] Running Half-Hourly Diagnostics (Raw settlement resolution)...")
    dataset_hh = service.get_matched_dataset(
        start_date=start_date,
        end_date=end_date,
        cutoff_param="day_ahead_1700",
        resolution="half_hourly",
    )
    diag_hh = dataset_hh.diagnostics
    print(f"      Total expected half-hourly slots: {diag_hh.total_expected_intervals} (31 days * 48 SP = 1488)")
    print(f"      Matched half-hourly intervals:    {diag_hh.matched_intervals_count}")
    print(f"      Resolution mismatch (:30 slots):  {diag_hh.resolution_mismatch_count}")
    print(f"      Genuine missing forecasts:        {diag_hh.missing_forecast_count}")
    print(f"      Missing actuals:                  {diag_hh.missing_actual_count}")

    print("\n" + "=" * 70)
    print("DAILY BREAKDOWN SUMMARY (Sample Days):")
    print("-" * 70)
    print(f"{'Date':<12} | {'Matched':<8} | {'MAE (MW)':<10} | {'RMSE (MW)':<10} | {'Bias (MW)':<10} | {'MAPE (%)':<8}")
    print("-" * 70)
    sample_dates = [
        date(2026, 1, 1),
        date(2026, 1, 7),
        date(2026, 1, 14),
        date(2026, 1, 21),
        date(2026, 1, 28),
        date(2026, 1, 31),
    ]
    for d in sample_dates:
        ov = service.get_overview(d, cutoff_param="day_ahead_1700", resolution="hourly")
        m = ov["metrics"]
        mae = f"{m['mae_mw']:.1f}" if m.get("mae_mw") is not None else "N/A"
        rmse = f"{m['rmse_mw']:.1f}" if m.get("rmse_mw") is not None else "N/A"
        bias = f"{m['signed_bias_mw']:.1f}" if m.get("signed_bias_mw") is not None else "N/A"
        mape = f"{m['mape_pct']:.1f}%" if m.get("mape_pct") is not None else "N/A"
        cnt = ov["diagnostics"]["matched_intervals_count"]
        print(f"{d.isoformat():<12} | {cnt:<8} | {mae:<10} | {rmse:<10} | {bias:<10} | {mape:<8}")

    print("=" * 70)
    print("INGESTION AND EVALUATION FINISHED SUCCESSFULLY.")


if __name__ == "__main__":
    ingest_and_evaluate_january()

