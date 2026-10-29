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
} from 'recharts';
import { formatIsoTime, formatIsoDateTime, formatMW, formatNumber } from '../utils/formatters';

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload || !payload.length) return null;

  const item = payload[0]?.payload || {};

  return (
    <div className="bg-base-100 border border-base-300 rounded-lg p-3 shadow-xl text-xs max-w-xs space-y-1.5 z-50">
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

        <div className="flex justify-between items-center text-success">
          <span className="font-semibold flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-success inline-block"></span> Actual Outturn:
          </span>
          <span className="font-mono font-bold">{formatMW(item.actualGeneration)}</span>
        </div>

        {item.signedError !== null && item.signedError !== undefined && (
          <div className="flex justify-between items-center text-base-content/80 pt-1 border-t border-base-200">
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
            <span>Forecast Lead Time:</span>
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

  // Check if any missing values exist to display a subtle notice
  const missingCount = intervals.filter(
    (i) => i.forecastGeneration === null || i.actualGeneration === null
  ).length;

  return (
    <div className="card bg-base-100 border border-base-300 shadow-sm p-4 lg:p-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
        <div>
          <h2 className="text-base font-bold text-base-content tracking-tight">
            Wind Generation: Forecast vs Actual Outturn
          </h2>
          <p className="text-xs text-base-content/60">
            {resolution === 'hourly'
              ? 'Aggregated 1-hour average MW power blocks (24 periods/day)'
              : 'Raw half-hourly settlement intervals (48 periods/day)'}
          </p>
        </div>

        {missingCount > 0 && (
          <div className="text-[11px] text-base-content/60 bg-base-200 px-2.5 py-1 rounded border border-base-300">
            Note: Discontinuous gaps represent unforecasted or missing intervals (never plotted as zero).
          </div>
        )}
      </div>

      <div className="w-full h-80 lg:h-96">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={intervals} margin={{ top: 10, right: 15, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="currentColor" className="text-base-300" opacity={0.6} />
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
            {/* Forecast Line: Primary Blue/Cyan, connectNulls=false ensures gaps are preserved */}
            <Line
              type="monotone"
              dataKey="forecastGeneration"
              name="WINDFOR Forecast (MW)"
              stroke="#0284c7"
              strokeWidth={2.5}
              dot={{ r: 2, fill: '#0284c7' }}
              activeDot={{ r: 5 }}
              connectNulls={false}
            />
            {/* Actual Outturn Line: Emerald/Green, connectNulls=false ensures gaps are preserved */}
            <Line
              type="monotone"
              dataKey="actualGeneration"
              name="FUELHH Actual (MW)"
              stroke="#10b981"
              strokeWidth={2.5}
              dot={{ r: 2, fill: '#10b981' }}
              activeDot={{ r: 5 }}
              connectNulls={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

