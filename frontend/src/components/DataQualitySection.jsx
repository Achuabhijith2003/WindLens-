import React from 'react';
import { Info, AlertCircle, CheckCircle2, Split, Database } from 'lucide-react';
import { formatNumber, formatPercent } from '../utils/formatters';

export default function DataQualitySection({ diagnostics = null, metrics = null, resolution = 'hourly' }) {
  if (!diagnostics || !metrics) return null;

  const {
    total_expected_intervals = 0,
    matched_intervals_count = 0,
    missing_actual_count = 0,
    missing_forecast_count = 0,
    resolution_mismatch_count = 0,
    future_forecasts_filtered_count = 0,
  } = diagnostics;

  const { mape_excluded_zero_count = 0, data_completeness_pct = 0 } = metrics;

  return (
    <div className="card bg-base-100 border border-base-300 shadow-sm p-4 lg:p-6 space-y-4">
      <div className="flex items-center justify-between border-b border-base-300 pb-3">
        <div className="flex items-center gap-2">
          <Database className="w-5 h-5 text-primary" />
          <h2 className="text-base font-bold text-base-content tracking-tight">
            Data Quality & Resolution Diagnostics
          </h2>
        </div>
        <span className="badge badge-sm badge-outline">
          Resolution Mode: <strong className="ml-1 uppercase">{resolution}</strong>
        </span>
      </div>

      {/* Resolution Explanation Alert */}
      <div role="alert" className="alert alert-info alert-soft text-xs sm:text-sm">
        <Info className="w-5 h-5 shrink-0" />
        <div>
          <div className="font-bold">Temporal Resolution Mechanics:</div>
          <p className="text-xs text-base-content/80 mt-0.5">
            Elexon WINDFOR forecasts are published at hourly delivery intervals (<code className="bg-base-200 px-1 py-0.5 rounded">:00</code>).
            {resolution === 'hourly' ? (
              <> In <strong>Hourly Mode</strong>, two 30-minute FUELHH outturn records (<code className="bg-base-200 px-1 py-0.5 rounded">:00</code> and <code className="bg-base-200 px-1 py-0.5 rounded">:30</code>) are aggregated by arithmetic mean into 1-hour average MW. This aligns units with zero interpolation.</>
            ) : (
              <> In <strong>Half-Hourly Mode</strong>, raw 30-minute outturn settlement blocks are preserved. Because WINDFOR publishes hourly forecasts, <code className="bg-base-200 px-1 py-0.5 rounded">:30</code> slots are designated as <strong>Resolution Mismatch</strong> and excluded from error metrics rather than falsely flagged as ingestion failures.</>
            )}
          </p>
        </div>
      </div>

      {/* Metrics Quality Breakdown Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <div className="bg-base-200/60 p-3 rounded-lg border border-base-300/60 text-center">
          <div className="text-[11px] font-semibold text-base-content/60 uppercase">Expected Slots</div>
          <div className="text-lg font-bold font-mono text-base-content mt-0.5">{total_expected_intervals}</div>
          <div className="text-[10px] text-base-content/50">{resolution === 'hourly' ? '24/day' : '48/day'}</div>
        </div>

        <div className="bg-base-200/60 p-3 rounded-lg border border-base-300/60 text-center">
          <div className="text-[11px] font-semibold text-success uppercase">Matched Pairs</div>
          <div className="text-lg font-bold font-mono text-success mt-0.5">{matched_intervals_count}</div>
          <div className="text-[10px] text-base-content/50">{formatPercent(data_completeness_pct)} coverage</div>
        </div>

        <div className="bg-base-200/60 p-3 rounded-lg border border-base-300/60 text-center">
          <div className="text-[11px] font-semibold text-warning uppercase">Resolution Mismatch</div>
          <div className="text-lg font-bold font-mono text-warning mt-0.5">{resolution_mismatch_count}</div>
          <div className="text-[10px] text-base-content/50">:30 unforecasted slots</div>
        </div>

        <div className="bg-base-200/60 p-3 rounded-lg border border-base-300/60 text-center">
          <div className="text-[11px] font-semibold text-error uppercase">Missing Forecasts</div>
          <div className="text-lg font-bold font-mono text-error mt-0.5">{missing_forecast_count}</div>
          <div className="text-[10px] text-base-content/50">Pipeline / lookahead gap</div>
        </div>

        <div className="bg-base-200/60 p-3 rounded-lg border border-base-300/60 text-center">
          <div className="text-[11px] font-semibold text-error uppercase">Missing Actuals</div>
          <div className="text-lg font-bold font-mono text-error mt-0.5">{missing_actual_count}</div>
          <div className="text-[10px] text-base-content/50">FUELHH outturn absent</div>
        </div>

        <div className="bg-base-200/60 p-3 rounded-lg border border-base-300/60 text-center">
          <div className="text-[11px] font-semibold text-info uppercase">Post-Cutoff Filtered</div>
          <div className="text-lg font-bold font-mono text-info mt-0.5">{future_forecasts_filtered_count}</div>
          <div className="text-[10px] text-base-content/50">Zero-lookahead filtered</div>
        </div>
      </div>

      {mape_excluded_zero_count > 0 && (
        <div className="text-xs text-base-content/70 bg-base-200 p-2.5 rounded border border-base-300 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-warning shrink-0" />
          <span>
            <strong>Zero Generation Protection:</strong> {mape_excluded_zero_count} interval(s) had actual generation equal to 0.0 MW and were excluded from the MAPE percentage denominator to avoid division-by-zero distortion.
          </span>
        </div>
      )}
    </div>
  );
}

