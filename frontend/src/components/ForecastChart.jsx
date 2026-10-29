import React from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  Brush,
} from 'recharts';
import { formatIsoTime, formatIsoDateTime, formatMW, formatNumber } from '../utils/formatters';
import { Zap, AlertCircle, ArrowUpRight, ArrowDownRight } from 'lucide-react';

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload || !payload.length) return null;

  const item = payload[0]?.payload || {};

  return (
    <div className="bg-base-100/95 backdrop-blur border border-base-300 rounded-lg p-3 shadow-xl text-xs max-w-xs space-y-1.5 z-50">
      <div className="font-bold border-b border-base-300 pb-1 text-base-content flex items-center justify-between">
        <span>{formatIsoDateTime(item.startTime)}</span>
        {item.settlementPeriod && (
          <span className="badge badge-xs badge-neutral font-mono">SP {item.settlementPeriod}</span>
        )}
      </div>

      <div className="space-y-1 pt-0.5">
        <div className="flex justify-between items-center text-primary">
          <span className="font-semibold flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-primary inline-block"></span> Forecast:
          </span>
          <span className="font-mono font-bold">{formatMW(item.forecastGeneration)}</span>
        </div>

        <div className="flex justify-between items-center text-secondary">
          <span className="font-semibold flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-secondary inline-block"></span> Actual Outturn:
          </span>
          <span className="font-mono font-bold">{formatMW(item.actualGeneration)}</span>
        </div>

        {item.signedError !== null && item.signedError !== undefined && (
          <div className="flex justify-between items-center text-base-content/85 pt-1 border-t border-base-200">
            <span>Error (FC - ACT):</span>
            <span className="font-mono font-semibold">
              {item.signedError > 0 ? `+${formatNumber(item.signedError)}` : formatNumber(item.signedError)} MW
              {item.percentageError !== null && item.percentageError !== undefined && (
                <span className="text-base-content/50 ml-1">({formatNumber(item.percentageError)}%)</span>
              )}
            </span>
          </div>
        )}

        {item.leadTimeHours !== null && item.leadTimeHours !== undefined && (
          <div className="flex justify-between items-center text-base-content/60 text-[11px]">
            <span>Cutoff Lead Time:</span>
            <span className="font-mono">{formatNumber(item.leadTimeHours)}h ahead</span>
          </div>
        )}

        {item.forecastPublishTime && (
          <div className="flex justify-between items-center text-base-content/60 text-[11px]">
            <span>Forecast Published:</span>
            <span className="font-mono">{formatIsoTime(item.forecastPublishTime)}</span>
          </div>
        )}

        <div className="pt-1 flex items-center justify-between text-[11px]">
          <span className="text-base-content/60">Status:</span>
          <span
            className={`badge badge-xs ${
              item.status === 'matched'
                ? 'badge-success'
                : item.status === 'resolution_mismatch'
                ? 'badge-warning'
                : 'badge-error'
            }`}
          >
            {item.status === 'resolution_mismatch' ? 'Resolution Mismatch (:30)' : item.status}
          </span>
        </div>
      </div>
    </div>
  );
}

export default function ForecastChart({ intervals = [], resolution = 'hourly' }) {
  if (!intervals || !intervals.length) {
    return (
      <div className="card bg-base-100 border border-base-300 p-8 text-center text-base-content/60">
        No generation intervals to display for the selected parameters.
      </div>
    );
  }

  // Calculate analytical highlights
  const matched = intervals.filter(
    (i) => i.actualGeneration !== null && i.forecastGeneration !== null
  );

  let peakForecast = null;
  let peakActual = null;
  let maxOverForecast = null;
  let maxUnderForecast = null;

  matched.forEach((i) => {
    if (!peakForecast || i.forecastGeneration > peakForecast.forecastGeneration) {
      peakForecast = i;
    }
    if (!peakActual || i.actualGeneration > peakActual.actualGeneration) {
      peakActual = i;
    }
    if (i.signedError !== null) {
      if (!maxOverForecast || i.signedError > maxOverForecast.signedError) {
        maxOverForecast = i;
      }
      if (!maxUnderForecast || i.signedError < maxUnderForecast.signedError) {
        maxUnderForecast = i;
      }
    }
  });

  const missingCount = intervals.filter(
    (i) => i.forecastGeneration === null || i.actualGeneration === null
  ).length;

  return (
    <div className="space-y-4">
      {/* Main Time Series Chart */}
      <div className="card bg-base-100 border border-base-300 shadow-sm p-4 lg:p-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
          <div>
            <h2 className="text-base font-bold text-base-content tracking-tight flex items-center gap-2">
              <span>Wind Generation: Forecast vs Actual Outturn</span>
              <span className="badge badge-xs badge-neutral font-mono">
                {resolution === 'hourly' ? '1-Hour MW Blocks' : '30-Min Settlement Periods'}
              </span>
            </h2>
            <p className="text-xs text-base-content/60">
              Interactive timeline with scrubber slider. Discontinuous line gaps represent missing intervals (never fabricated).
            </p>
          </div>

          {missingCount > 0 && (
            <div className="text-[11px] text-warning bg-warning/10 px-2.5 py-1 rounded border border-warning/20 flex items-center gap-1.5">
              <AlertCircle className="w-3.5 h-3.5" />
              <span>{missingCount} missing/unmatched intervals visible as gaps</span>
            </div>
          )}
        </div>

        <div className="w-full h-80 lg:h-96">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={intervals} margin={{ top: 10, right: 15, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="currentColor" className="text-base-300" opacity={0.5} />
              <XAxis
                dataKey="startTime"
                tickFormatter={(val) => formatIsoTime(val)}
                tick={{ fontSize: 11, fill: 'currentColor' }}
                className="text-base-content/60"
                minTickGap={25}
              />
              <YAxis
                tickFormatter={(val) => `${(val / 1000).toFixed(1)}k`}
                tick={{ fontSize: 11, fill: 'currentColor' }}
                className="text-base-content/60"
                unit=" MW"
                width={65}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend
                verticalAlign="top"
                align="right"
                wrapperStyle={{ paddingBottom: '10px', fontSize: '12px' }}
              />
              {/* Forecast Line: Primary Slate-Blue */}
              <Line
                type="monotone"
                dataKey="forecastGeneration"
                name="WINDFOR Forecast (MW)"
                stroke="#38bdf8"
                strokeWidth={2.2}
                dot={{ r: 2, fill: '#38bdf8' }}
                activeDot={{ r: 5 }}
                connectNulls={false}
              />
              {/* Actual Outturn Line: Secondary Teal */}
              <Line
                type="monotone"
                dataKey="actualGeneration"
                name="FUELHH Actual (MW)"
                stroke="#34d399"
                strokeWidth={2.2}
                dot={{ r: 2, fill: '#34d399' }}
                activeDot={{ r: 5 }}
                connectNulls={false}
              />
              {/* Interactive Timeline Brush */}
              <Brush
                dataKey="startTime"
                height={26}
                stroke="#64748b"
                fill="rgba(100, 116, 139, 0.15)"
                tickFormatter={(val) => formatIsoTime(val)}
                travellerWidth={10}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Analytical Peak & Extreme Highlights */}
      {matched.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {/* Peak Forecast */}
          <div className="card bg-base-100 border border-base-300 p-3.5 shadow-xs">
            <div className="flex items-center justify-between text-xs text-base-content/60 mb-1">
              <span className="font-semibold uppercase text-[10px] tracking-wider">Peak Forecast</span>
              <Zap className="w-3.5 h-3.5 text-primary" />
            </div>
            <div className="text-lg font-bold font-mono text-base-content">
              {formatMW(peakForecast?.forecastGeneration)}
            </div>
            <div className="text-[11px] text-base-content/60 truncate mt-0.5">
              At {formatIsoDateTime(peakForecast?.startTime)}
            </div>
          </div>

          {/* Peak Actual */}
          <div className="card bg-base-100 border border-base-300 p-3.5 shadow-xs">
            <div className="flex items-center justify-between text-xs text-base-content/60 mb-1">
              <span className="font-semibold uppercase text-[10px] tracking-wider">Peak Actual Outturn</span>
              <Zap className="w-3.5 h-3.5 text-secondary" />
            </div>
            <div className="text-lg font-bold font-mono text-base-content">
              {formatMW(peakActual?.actualGeneration)}
            </div>
            <div className="text-[11px] text-base-content/60 truncate mt-0.5">
              At {formatIsoDateTime(peakActual?.startTime)}
            </div>
          </div>

          {/* Largest Over-Forecast */}
          <div className="card bg-base-100 border border-base-300 p-3.5 shadow-xs">
            <div className="flex items-center justify-between text-xs text-warning mb-1">
              <span className="font-semibold uppercase text-[10px] tracking-wider">Max Over-Forecast</span>
              <ArrowUpRight className="w-3.5 h-3.5" />
            </div>
            <div className="text-lg font-bold font-mono text-warning">
              {maxOverForecast?.signedError !== null && maxOverForecast?.signedError > 0
                ? `+${formatNumber(maxOverForecast.signedError)} MW`
                : '—'}
            </div>
            <div className="text-[11px] text-base-content/60 truncate mt-0.5">
              At {formatIsoTime(maxOverForecast?.startTime)} (FC &gt; ACT)
            </div>
          </div>

          {/* Largest Under-Forecast */}
          <div className="card bg-base-100 border border-base-300 p-3.5 shadow-xs">
            <div className="flex items-center justify-between text-xs text-info mb-1">
              <span className="font-semibold uppercase text-[10px] tracking-wider">Max Under-Forecast</span>
              <ArrowDownRight className="w-3.5 h-3.5" />
            </div>
            <div className="text-lg font-bold font-mono text-info">
              {maxUnderForecast?.signedError !== null
                ? `${formatNumber(maxUnderForecast.signedError)} MW`
                : '—'}
            </div>
            <div className="text-[11px] text-base-content/60 truncate mt-0.5">
              At {formatIsoTime(maxUnderForecast?.startTime)} (ACT &gt; FC)
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
