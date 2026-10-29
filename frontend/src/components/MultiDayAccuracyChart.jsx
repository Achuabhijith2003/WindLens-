import React, { useState, useMemo } from 'react';
import {
  ResponsiveContainer,
  ComposedChart,
  LineChart,
  BarChart,
  Line,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
  Cell,
} from 'recharts';
import { formatNumber, formatPercent } from '../utils/formatters';
import { TrendingUp, BarChart3, Activity, Award, AlertTriangle, Layers, Percent } from 'lucide-react';

function formatChartDate(dateStr) {
  if (!dateStr) return '';
  try {
    const parts = dateStr.split('-');
    if (parts.length === 3) {
      const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
      const monthIdx = parseInt(parts[1], 10) - 1;
      return `${parts[2]} ${monthNames[monthIdx] || parts[1]}`;
    }
    return dateStr;
  } catch {
    return dateStr;
  }
}

function MultiDayTooltip({ active, payload, label }) {
  if (!active || !payload || !payload.length) return null;
  const item = payload[0]?.payload || {};

  return (
    <div className="bg-base-100/95 backdrop-blur border border-base-300 rounded-lg p-3 shadow-xl text-xs space-y-1.5 z-50 min-w-[200px]">
      <div className="font-bold border-b border-base-300 pb-1 text-base-content flex items-center justify-between">
        <span>{formatChartDate(item.date)} ({item.date})</span>
        <span className="badge badge-xs badge-neutral font-mono">
          {item.matchedCount}/{item.expectedCount} slots
        </span>
      </div>

      <div className="space-y-1 pt-0.5">
        <div className="flex justify-between items-center text-primary">
          <span className="font-semibold flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-primary inline-block"></span> MAE:
          </span>
          <span className="font-mono font-bold">
            {item.mae !== null ? `${formatNumber(item.mae)} MW` : '—'}
          </span>
        </div>

        <div className="flex justify-between items-center text-secondary">
          <span className="font-semibold flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-secondary inline-block"></span> RMSE:
          </span>
          <span className="font-mono font-bold">
            {item.rmse !== null ? `${formatNumber(item.rmse)} MW` : '—'}
          </span>
        </div>

        <div className="flex justify-between items-center text-base-content/90 pt-1 border-t border-base-200">
          <span>Signed Bias:</span>
          <span className="font-mono font-bold flex items-center gap-1">
            {item.signedBias !== null ? (
              <span className={item.signedBias > 0 ? 'text-warning' : 'text-info'}>
                {item.signedBias > 0 ? `+${formatNumber(item.signedBias)}` : formatNumber(item.signedBias)} MW
              </span>
            ) : (
              '—'
            )}
          </span>
        </div>

        <div className="flex justify-between items-center text-base-content/75">
          <span>MAPE:</span>
          <span className="font-mono font-bold">
            {item.mape !== null ? `${formatNumber(item.mape)}%` : '—'}
          </span>
        </div>
      </div>
    </div>
  );
}

export default function MultiDayAccuracyChart({
  dailyBreakdown = [],
  fromDate = '',
  toDate = '',
  cutoff = 'day_ahead_1700',
  resolution = 'hourly',
}) {
  const [chartMode, setChartMode] = useState('mae_rmse'); // 'mae_rmse', 'bias', 'mape', 'combined'

  // Flatten and prepare daily data
  const chartData = useMemo(() => {
    return dailyBreakdown.map((day) => ({
      date: day.date,
      formattedDate: formatChartDate(day.date),
      mae: day.metrics?.mae_mw ?? null,
      rmse: day.metrics?.rmse_mw ?? null,
      signedBias: day.metrics?.signed_bias_mw ?? null,
      mape: day.metrics?.mape_pct ?? null,
      matchedCount: day.matchedCount,
      expectedCount: day.expectedCount,
      completeness: day.metrics?.data_completeness_pct ?? null,
    }));
  }, [dailyBreakdown]);

  // Compute multi-day highlights
  const highlights = useMemo(() => {
    const valid = chartData.filter((d) => d.mae !== null);
    if (!valid.length) return null;

    let bestDay = valid[0];
    let worstDay = valid[0];
    let totalMae = 0;
    let overForecastDays = 0;
    let underForecastDays = 0;

    valid.forEach((d) => {
      if (d.mae < bestDay.mae) bestDay = d;
      if (d.mae > worstDay.mae) worstDay = d;
      totalMae += d.mae;
      if (d.signedBias > 0) overForecastDays += 1;
      if (d.signedBias < 0) underForecastDays += 1;
    });

    const avgMae = totalMae / valid.length;

    return {
      bestDay,
      worstDay,
      avgMae,
      overForecastDays,
      underForecastDays,
      totalDays: valid.length,
    };
  }, [chartData]);

  if (!dailyBreakdown || !dailyBreakdown.length) {
    return null;
  }

  return (
    <div className="card bg-base-100 border border-base-300 shadow-sm p-4 lg:p-6 space-y-4">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-base-300 pb-3">
        <div>
          <h2 className="text-base font-bold text-base-content tracking-tight flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-primary" />
            <span>Multi-Day Accuracy & Bias Evolution</span>
            <span className="badge badge-sm badge-outline font-mono text-[11px]">
              {fromDate} to {toDate}
            </span>
          </h2>
          <p className="text-xs text-base-content/60">
            Day-by-day forecast accuracy trends under cutoff: <strong className="font-mono text-primary">{cutoff}</strong> ({resolution})
          </p>
        </div>

        {/* View Mode Toggle */}
        <div className="join" role="group" aria-label="Multi-day chart mode">
          <button
            type="button"
            onClick={() => setChartMode('mae_rmse')}
            className={`btn btn-xs join-item ${
              chartMode === 'mae_rmse' ? 'btn-active btn-primary' : 'btn-outline border-base-300'
            }`}
          >
            MAE & RMSE (MW)
          </button>
          <button
            type="button"
            onClick={() => setChartMode('bias')}
            className={`btn btn-xs join-item ${
              chartMode === 'bias' ? 'btn-active btn-primary' : 'btn-outline border-base-300'
            }`}
          >
            Signed Bias (MW)
          </button>
          <button
            type="button"
            onClick={() => setChartMode('combined')}
            className={`btn btn-xs join-item ${
              chartMode === 'combined' ? 'btn-active btn-primary' : 'btn-outline border-base-300'
            }`}
          >
            Combined
          </button>
          <button
            type="button"
            onClick={() => setChartMode('mape')}
            className={`btn btn-xs join-item ${
              chartMode === 'mape' ? 'btn-active btn-primary' : 'btn-outline border-base-300'
            }`}
          >
            MAPE (%)
          </button>
        </div>
      </div>

      {/* Main Chart Area */}
      <div className="w-full h-80 lg:h-96">
        <ResponsiveContainer width="100%" height="100%">
          {/* Mode 1: MAE & RMSE Trend */}
          {chartMode === 'mae_rmse' && (
            <LineChart data={chartData} margin={{ top: 15, right: 15, bottom: 10, left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="currentColor" className="text-base-300" opacity={0.5} />
              <XAxis
                dataKey="formattedDate"
                tick={{ fontSize: 11, fill: 'currentColor' }}
                className="text-base-content/60"
              />
              <YAxis
                unit=" MW"
                tickFormatter={(val) => `${(val / 1000).toFixed(1)}k`}
                tick={{ fontSize: 11, fill: 'currentColor' }}
                className="text-base-content/60"
              />
              <Tooltip content={<MultiDayTooltip />} />
              <Legend verticalAlign="top" align="right" wrapperStyle={{ paddingBottom: '10px', fontSize: '12px' }} />
              <Line
                type="monotone"
                dataKey="mae"
                name="Daily MAE (MW)"
                stroke="#38bdf8"
                strokeWidth={2.5}
                dot={{ r: 4, fill: '#38bdf8' }}
                activeDot={{ r: 6 }}
              />
              <Line
                type="monotone"
                dataKey="rmse"
                name="Daily RMSE (MW)"
                stroke="#818cf8"
                strokeWidth={2.5}
                strokeDasharray="4 4"
                dot={{ r: 4, fill: '#818cf8' }}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          )}

          {/* Mode 2: Signed Bias by Day */}
          {chartMode === 'bias' && (
            <BarChart data={chartData} margin={{ top: 15, right: 15, bottom: 10, left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="currentColor" className="text-base-300" opacity={0.5} />
              <XAxis
                dataKey="formattedDate"
                tick={{ fontSize: 11, fill: 'currentColor' }}
                className="text-base-content/60"
              />
              <YAxis
                unit=" MW"
                tick={{ fontSize: 11, fill: 'currentColor' }}
                className="text-base-content/60"
              />
              <Tooltip content={<MultiDayTooltip />} />
              <ReferenceLine y={0} stroke="#94a3b8" strokeWidth={1.5} />
              <Bar dataKey="signedBias" name="Daily Signed Bias (MW)" radius={[4, 4, 0, 0]}>
                {chartData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={entry.signedBias >= 0 ? '#f59e0b' : '#0284c7'}
                  />
                ))}
              </Bar>
            </BarChart>
          )}

          {/* Mode 3: Combined MAE and Signed Bias */}
          {chartMode === 'combined' && (
            <ComposedChart data={chartData} margin={{ top: 15, right: 15, bottom: 10, left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="currentColor" className="text-base-300" opacity={0.5} />
              <XAxis
                dataKey="formattedDate"
                tick={{ fontSize: 11, fill: 'currentColor' }}
                className="text-base-content/60"
              />
              <YAxis
                unit=" MW"
                tick={{ fontSize: 11, fill: 'currentColor' }}
                className="text-base-content/60"
              />
              <Tooltip content={<MultiDayTooltip />} />
              <Legend verticalAlign="top" align="right" wrapperStyle={{ paddingBottom: '10px', fontSize: '12px' }} />
              <ReferenceLine y={0} stroke="#94a3b8" />
              <Bar
                dataKey="mae"
                name="Daily MAE (MW)"
                fill="#38bdf8"
                opacity={0.45}
                radius={[4, 4, 0, 0]}
              />
              <Line
                type="monotone"
                dataKey="signedBias"
                name="Signed Bias (MW)"
                stroke="#f59e0b"
                strokeWidth={2.5}
                dot={{ r: 4, fill: '#f59e0b' }}
              />
            </ComposedChart>
          )}

          {/* Mode 4: MAPE (%) Trend */}
          {chartMode === 'mape' && (
            <LineChart data={chartData} margin={{ top: 15, right: 15, bottom: 10, left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="currentColor" className="text-base-300" opacity={0.5} />
              <XAxis
                dataKey="formattedDate"
                tick={{ fontSize: 11, fill: 'currentColor' }}
                className="text-base-content/60"
              />
              <YAxis
                unit="%"
                tick={{ fontSize: 11, fill: 'currentColor' }}
                className="text-base-content/60"
              />
              <Tooltip content={<MultiDayTooltip />} />
              <Legend verticalAlign="top" align="right" wrapperStyle={{ paddingBottom: '10px', fontSize: '12px' }} />
              <Line
                type="monotone"
                dataKey="mape"
                name="Daily MAPE (%)"
                stroke="#ec4899"
                strokeWidth={2.5}
                dot={{ r: 4, fill: '#ec4899' }}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          )}
        </ResponsiveContainer>
      </div>

      {/* Multi-Day Range Highlights Cards */}
      {highlights && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 pt-2">
          {/* Best Performing Day */}
          <div className="card bg-base-200/60 border border-base-300 p-3 shadow-xs">
            <div className="flex items-center justify-between text-xs text-success mb-1">
              <span className="font-semibold uppercase text-[10px] tracking-wider">Most Accurate Day</span>
              <Award className="w-3.5 h-3.5" />
            </div>
            <div className="text-lg font-bold font-mono text-base-content">
              {formatNumber(highlights.bestDay?.mae)} MW
            </div>
            <div className="text-[11px] text-base-content/60 truncate mt-0.5">
              {formatChartDate(highlights.bestDay?.date)} (Lowest MAE)
            </div>
          </div>

          {/* Worst Day */}
          <div className="card bg-base-200/60 border border-base-300 p-3 shadow-xs">
            <div className="flex items-center justify-between text-xs text-warning mb-1">
              <span className="font-semibold uppercase text-[10px] tracking-wider">Highest Error Day</span>
              <AlertTriangle className="w-3.5 h-3.5" />
            </div>
            <div className="text-lg font-bold font-mono text-warning">
              {formatNumber(highlights.worstDay?.mae)} MW
            </div>
            <div className="text-[11px] text-base-content/60 truncate mt-0.5">
              {formatChartDate(highlights.worstDay?.date)} (Peak MAE)
            </div>
          </div>

          {/* Average Daily MAE */}
          <div className="card bg-base-200/60 border border-base-300 p-3 shadow-xs">
            <div className="flex items-center justify-between text-xs text-primary mb-1">
              <span className="font-semibold uppercase text-[10px] tracking-wider">Mean Daily MAE</span>
              <TrendingUp className="w-3.5 h-3.5" />
            </div>
            <div className="text-lg font-bold font-mono text-base-content">
              {formatNumber(highlights.avgMae)} MW
            </div>
            <div className="text-[11px] text-base-content/60 truncate mt-0.5">
              Across {highlights.totalDays} evaluated days
            </div>
          </div>

          {/* Persistent Bias Split */}
          <div className="card bg-base-200/60 border border-base-300 p-3 shadow-xs">
            <div className="flex items-center justify-between text-xs text-base-content/70 mb-1">
              <span className="font-semibold uppercase text-[10px] tracking-wider">Bias Distribution</span>
              <Activity className="w-3.5 h-3.5 text-secondary" />
            </div>
            <div className="text-lg font-bold font-mono text-base-content flex items-center gap-1.5">
              <span className="text-warning text-sm font-semibold">{highlights.overForecastDays} Over</span>
              <span className="text-base-content/40">•</span>
              <span className="text-info text-sm font-semibold">{highlights.underForecastDays} Under</span>
            </div>
            <div className="text-[11px] text-base-content/60 truncate mt-0.5">
              {highlights.overForecastDays > highlights.underForecastDays ? 'Predominantly Over-forecasted' : 'Predominantly Under-forecasted'}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

