import React from 'react';
import { TrendingUp, TrendingDown, Gauge, Target, CheckCircle, Percent } from 'lucide-react';
import { formatNumber, formatPercent } from '../utils/formatters';

export default function KpiCards({ metrics = null, resolution = 'hourly' }) {
  if (!metrics) {
    return (
      <div className="stats stats-vertical lg:stats-horizontal shadow-sm bg-base-100 border border-base-300 w-full animate-pulse">
        <div className="stat">
          <div className="stat-title">MAE</div>
          <div className="stat-value text-base-content/30 text-2xl">Loading...</div>
        </div>
      </div>
    );
  }

  const {
    mae_mw,
    rmse_mw,
    signed_bias_mw,
    mape_pct,
    mape_excluded_zero_count,
    matched_intervals_count,
    expected_interval_count,
    data_completeness_pct,
  } = metrics;

  const isOverForecasting = (signed_bias_mw || 0) > 0;
  const isZeroBias = (signed_bias_mw || 0) === 0;

  return (
    <div className="stats stats-vertical sm:stats-horizontal shadow-sm bg-base-100 border border-base-300 w-full grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 divide-y sm:divide-y-0 sm:divide-x divide-base-300">
      {/* 1. MAE */}
      <div className="stat p-3.5 lg:p-4">
        <div className="stat-figure text-primary/70 hidden lg:block">
          <Target className="w-6 h-6" />
        </div>
        <div className="stat-title text-xs font-semibold uppercase tracking-wider text-base-content/70">
          MAE
        </div>
        <div className="stat-value text-xl lg:text-2xl font-bold font-mono tracking-tight text-base-content">
          {mae_mw !== null && mae_mw !== undefined ? formatNumber(mae_mw) : '—'}
          <span className="text-xs font-normal text-base-content/60 ml-1">MW</span>
        </div>
        <div className="stat-desc text-[11px] text-base-content/60">
          Mean Absolute Error
        </div>
      </div>

      {/* 2. RMSE */}
      <div className="stat p-3.5 lg:p-4">
        <div className="stat-figure text-primary/70 hidden lg:block">
          <Gauge className="w-6 h-6" />
        </div>
        <div className="stat-title text-xs font-semibold uppercase tracking-wider text-base-content/70">
          RMSE
        </div>
        <div className="stat-value text-xl lg:text-2xl font-bold font-mono tracking-tight text-base-content">
          {rmse_mw !== null && rmse_mw !== undefined ? formatNumber(rmse_mw) : '—'}
          <span className="text-xs font-normal text-base-content/60 ml-1">MW</span>
        </div>
        <div className="stat-desc text-[11px] text-base-content/60">
          Root Mean Square Error
        </div>
      </div>

      {/* 3. Signed Bias */}
      <div className="stat p-3.5 lg:p-4">
        <div className="stat-figure text-primary/70 hidden lg:block">
          {isOverForecasting ? (
            <TrendingUp className="w-6 h-6 text-warning" />
          ) : (
            <TrendingDown className="w-6 h-6 text-info" />
          )}
        </div>
        <div className="stat-title text-xs font-semibold uppercase tracking-wider text-base-content/70">
          Signed Bias
        </div>
        <div className="stat-value text-xl lg:text-2xl font-bold font-mono tracking-tight text-base-content flex items-center">
          {signed_bias_mw !== null && signed_bias_mw !== undefined ? (
            <>
              {signed_bias_mw > 0 ? `+${formatNumber(signed_bias_mw)}` : formatNumber(signed_bias_mw)}
              <span className="text-xs font-normal text-base-content/60 ml-1">MW</span>
            </>
          ) : (
            '—'
          )}
        </div>
        <div className="stat-desc text-[11px]">
          {signed_bias_mw !== null && signed_bias_mw !== undefined ? (
            <span className={`badge badge-xs ${isOverForecasting ? 'badge-warning' : isZeroBias ? 'badge-neutral' : 'badge-info'}`}>
              {isOverForecasting ? 'Over-forecasting' : isZeroBias ? 'Unbiased' : 'Under-forecasting'}
            </span>
          ) : (
            <span className="text-base-content/60">Forecast minus actual</span>
          )}
        </div>
      </div>

      {/* 4. MAPE */}
      <div className="stat p-3.5 lg:p-4">
        <div className="stat-figure text-primary/70 hidden lg:block">
          <Percent className="w-6 h-6" />
        </div>
        <div className="stat-title text-xs font-semibold uppercase tracking-wider text-base-content/70">
          MAPE
        </div>
        <div className="stat-value text-xl lg:text-2xl font-bold font-mono tracking-tight text-base-content">
          {mape_pct !== null && mape_pct !== undefined ? formatPercent(mape_pct, 2) : '—'}
        </div>
        <div className="stat-desc text-[11px] text-base-content/60 truncate" title={`${mape_excluded_zero_count || 0} zero-actual intervals excluded`}>
          {mape_excluded_zero_count > 0 ? `${mape_excluded_zero_count} zeros excluded` : 'All actuals > 0'}
        </div>
      </div>

      {/* 5. Completeness */}
      <div className="stat p-3.5 lg:p-4 col-span-2 sm:col-span-1">
        <div className="stat-figure text-success hidden lg:block">
          <CheckCircle className="w-6 h-6" />
        </div>
        <div className="stat-title text-xs font-semibold uppercase tracking-wider text-base-content/70">
          Completeness
        </div>
        <div className="stat-value text-xl lg:text-2xl font-bold font-mono tracking-tight text-base-content">
          {formatPercent(data_completeness_pct)}
        </div>
        <div className="stat-desc text-[11px] text-base-content/60">
          {matched_intervals_count} of {expected_interval_count} intervals ({resolution})
        </div>
      </div>
    </div>
  );
}
