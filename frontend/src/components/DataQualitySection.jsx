import React from 'react';
import { Info, AlertCircle, CheckCircle2, Split, Database, ShieldCheck, Clock, BookOpen } from 'lucide-react';
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
    <div className="space-y-4">
      <div className="card bg-base-100 border border-base-300 shadow-sm p-4 lg:p-6 space-y-4">
        <div className="flex items-center justify-between border-b border-base-300 pb-3">
          <div className="flex items-center gap-2">
            <Database className="w-5 h-5 text-primary" />
            <div>
              <h2 className="text-base font-bold text-base-content tracking-tight">
                Data Quality & Pipeline Integrity
              </h2>
              <p className="text-xs text-base-content/60">
                Audited ingestion metrics from Elexon BMRS FUELHH & WINDFOR streams
              </p>
            </div>
          </div>
          <span className="badge badge-sm badge-outline font-mono text-[11px]">
            Resolution: <strong className="ml-1 uppercase text-primary">{resolution}</strong>
          </span>
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
          <div className="text-xs text-base-content/75 bg-base-200 p-2.5 rounded border border-base-300 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-warning shrink-0" />
            <span>
              <strong>Zero Generation Protection:</strong> {mape_excluded_zero_count} interval(s) had actual generation equal to 0.0 MW and were excluded from the MAPE percentage denominator to prevent division-by-zero distortion.
            </span>
          </div>
        )}
      </div>

      {/* Market Mechanics Educational Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Day-Ahead Gate Closure Mechanics */}
        <div className="card bg-base-100 border border-base-300 p-4 lg:p-5 space-y-2.5 shadow-xs">
          <div className="flex items-center gap-2 text-primary font-bold text-sm">
            <Clock className="w-4 h-4" />
            <span>Day-Ahead Decision Cutoff Mechanics</span>
          </div>
          <p className="text-xs text-base-content/70 leading-relaxed">
            In Great Britain's power system, market participants formulate trading positions and schedule dispatch before Day-Ahead gate closure. For any delivery date <strong className="font-mono text-base-content">D</strong>, the standard Day-Ahead decision cutoff occurs at <strong className="font-mono text-base-content">D−1 17:00:00 UTC</strong>.
          </p>
          <div className="text-xs bg-base-200/70 p-2.5 rounded border border-base-300/70 text-base-content/80">
            <span className="font-semibold text-warning">Zero-Lookahead Guarantee:</span> Only forecasts with <code className="font-mono text-primary font-semibold">publishTime ≤ Cutoff</code> are selected. Forecasts published after the cutoff are rigorously rejected to eliminate hindsight bias.
          </div>
        </div>

        {/* Elexon BMRS Settlement Periods & Aggregation */}
        <div className="card bg-base-100 border border-base-300 p-4 lg:p-5 space-y-2.5 shadow-xs">
          <div className="flex items-center gap-2 text-secondary font-bold text-sm">
            <BookOpen className="w-4 h-4" />
            <span>Settlement Period Resolution Alignment</span>
          </div>
          <p className="text-xs text-base-content/70 leading-relaxed">
            Elexon publishes outturn generation (<strong className="font-mono text-base-content">FUELHH</strong>) across 48 half-hourly Settlement Periods daily, while National Grid ESO WINDFOR models issue forecasts at hourly intervals (<strong className="font-mono text-base-content">:00</strong>).
          </p>
          <div className="text-xs bg-base-200/70 p-2.5 rounded border border-base-300/70 text-base-content/80">
            <span className="font-semibold text-secondary">Defensible Aggregation:</span> In Hourly Mode, paired half-hours <code className="font-mono text-base-content">(SP₁ + SP₂) / 2.0</code> are averaged into clean 1-hour energy blocks. Half-hourly mode preserves raw settlement granularity with explicit mismatch indicators.
          </div>
        </div>
      </div>
    </div>
  );
}
