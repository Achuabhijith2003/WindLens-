"""Live ingestion verification script for WINDFOR and FUELHH streams."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from datetime import date, datetime, timezone
from backend.services.data_service import DataService

def run_live_verification():
    print("=== WINDLENS LIVE INGESTION & MATCHING VERIFICATION ===")
    service = DataService(enable_disk_cache=True)

    start_date = date(2026, 1, 1)
    end_date = date(2026, 1, 3)

    print(f"\n1. Ingesting FUELHH actuals for delivery dates: {start_date} to {end_date}...")
    actuals = service.fetch_actuals_for_delivery_dates(start_date, end_date)
    print(f"   -> Retrieved {len(actuals)} FUELHH actual records")
    if actuals:
        earliest_act_pub = min(a.publishTime for a in actuals)
        latest_act_pub = max(a.publishTime for a in actuals)
        earliest_act_start = min(a.startTime for a in actuals)
        latest_act_start = max(a.startTime for a in actuals)
        print(f"   -> Actuals publish time range: {earliest_act_pub} to {latest_act_pub}")
        print(f"   -> Actuals delivery startTime range: {earliest_act_start} to {latest_act_start}")

    print(f"\n2. Ingesting WINDFOR forecasts (with December 2025 lookback) for delivery: {start_date} to {end_date}...")
    forecasts = service.fetch_forecasts_for_delivery_dates(start_date, end_date)
    print(f"   -> Retrieved {len(forecasts)} WINDFOR forecast records")
    if forecasts:
        earliest_fc_pub = min(f.publishTime for f in forecasts)
        latest_fc_pub = max(f.publishTime for f in forecasts)
        earliest_fc_start = min(f.startTime for f in forecasts)
        latest_fc_start = max(f.startTime for f in forecasts)
        print(f"   -> Forecasts publish time range: {earliest_fc_pub} to {latest_fc_pub}")
        print(f"   -> Forecasts delivery startTime range: {earliest_fc_start} to {latest_fc_start}")

    print("\n3. Testing Hourly Matching (Aggregated 1-hour average MW)...")
    dataset_hourly = service.get_matched_dataset(start_date, end_date, cutoff_param="day_ahead_1700", resolution="hourly")
    print(f"   -> Total expected hourly intervals: {dataset_hourly.diagnostics.total_expected_intervals}")
    print(f"   -> Matched hourly intervals: {dataset_hourly.diagnostics.matched_intervals_count}")
    print(f"   -> Missing forecast count: {dataset_hourly.diagnostics.missing_forecast_count}")
    print(f"   -> Missing actual count: {dataset_hourly.diagnostics.missing_actual_count}")
    print(f"   -> Post-cutoff forecasts excluded: {dataset_hourly.diagnostics.future_forecasts_filtered_count}")

    overview = service.get_overview(date(2026, 1, 1), cutoff_param="day_ahead_1700", resolution="hourly")
    metrics = overview["metrics"]
    print(f"\n4. Accuracy Metrics for 2026-01-01 (Hourly Resolution):")
    print(f"   -> MAE: {metrics['mae_mw']} MW")
    print(f"   -> RMSE: {metrics['rmse_mw']} MW")
    print(f"   -> Signed Bias: {metrics['signed_bias_mw']} MW")
    print(f"   -> MAPE: {metrics['mape_pct']}% (Excluded zeros: {metrics['mape_excluded_zero_count']})")
    print(f"   -> Completeness: {metrics['data_completeness_pct']}%")

    print("\n5. Testing Half-Hourly Matching (Raw settlement view)...")
    dataset_hh = service.get_matched_dataset(start_date, end_date, cutoff_param="day_ahead_1700", resolution="half_hourly")
    print(f"   -> Total expected half-hourly intervals: {dataset_hh.diagnostics.total_expected_intervals}")
    print(f"   -> Matched half-hourly intervals: {dataset_hh.diagnostics.matched_intervals_count}")
    print(f"   -> Resolution mismatch (:30 slots unforecasted): {dataset_hh.diagnostics.resolution_mismatch_count}")
    print(f"   -> Genuine missing forecast count: {dataset_hh.diagnostics.missing_forecast_count}")

    print("\n=== VERIFICATION COMPLETE ===")

if __name__ == "__main__":
    run_live_verification()
