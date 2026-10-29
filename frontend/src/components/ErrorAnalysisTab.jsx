import React, { useMemo } from 'react';
import {
  ResponsiveContainer,
  ComposedChart,
  BarChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  Cell,
} from 'recharts';
import { formatIsoTime, formatIsoDateTime, formatMW, formatNumber } from '../utils/formatters';
import { AlertTriangle, Clock, ArrowUpRight, ArrowDownRight, Activity } from 'lucide-react';

function ErrorTimelineTooltip({ active, payload }) {
  if (!active || !payload || !payload.length) return null;
  const item = payload[0]?.payload || {};

  return (
    <div className="bg-base-100/95 backdrop-blur border border-base-300 rounded-lg p-3 shadow-xl text-xs space-y-1 z-50">
      <div className="font-bold border-b border-base-300 pb-1 text-base-content flex justify-between items-center">
        <span>{formatIsoDateTime(item.startTime)}</span>
        <span
          className={`badge badge-xs ${
            item.signedError > 0
              ? 'badge-warning text-warning-content'
              : item.signedError < 0
              ? 'badge-info text-info-content'
              : 'badge-neutral'
          }`}
        >
          {item.signedError > 0 ? 'Over-forecast' : item.signedError < 0 ? 'Under-forecast' : 'Exact'}
        </span>
      </div>
      <div className="pt-1 flex justify-between gap-4 text-base-content/80">
        <span>Error (FC - ACT):</span>
        <span className="font-mono font-bold">
          {item.signedError > 0 ? `+${formatNumber(item.signedError)}` : formatNumber(item.signedError)} MW
        </span>
      </div>
      <div className="flex justify-between gap-4 text-primary">
        <span>Forecast Generation:</span>
        <span className="font-mono">{formatMW(item.forecastGeneration)}</span>
      </div>
      <div className="flex justify-between gap-4 text-secondary">
        <span>Actual Outturn:</span>
        <span className="font-mono">{formatMW(item.actualGeneration)}</span>
      </div>
      {item.leadTimeHours !== null && (
        <div className="text-[11px] text-base-content/60 pt-1 border-t border-base-200">
          Lead time: {item.leadTimeHours}h ahead
        </div>
      )}
    </div>
  );
}

export default function ErrorAnalysisTab({ intervals = [], metrics = null, resolution = 'hourly' }) {
  const matched = useMemo(() => {
    return intervals.filter(
      (i) => i.actualGeneration !== null && i.forecastGeneration !== null && i.signedError !== null
    );
  }, [intervals]);

  // 1. Hourly Diurnal Error Profile (00:00 - 23:00 UTC)
  const diurnalData = useMemo(() => {
    const hours = Array.from({ length: 24 }, (_, i) => ({
      hour: i,
      label: `${String(i).padStart(2, '0')}:00`,
      totalError: 0,
      count: 0,
    }));

    matched.forEach((item) => {
      if (item.startTime) {
        const d = new Date(item.startTime);
        const h = d.getUTCHours();
        if (h >= 0 && h < 24) {
          hours[h].totalError += item.signedError;
          hours[h].count += 1;
        }
      }
    });

    return hours.map((h) => ({
      label: h.label,
      avgError: h.count > 0 ? Math.round((h.totalError / h.count) * 10) / 10 : 0,
      count: h.count,
    }));
  }, [matched]);

  // 2. Top Over-Forecasting Outliers (Forecast >> Actual)
  const topOverForecasts = useMemo(() => {
    return [...matched]
      .filter((i) => i.signedError > 0)
      .sort((a, b) => b.signedError - a.signedError)
      .slice(0, 4);
  }, [matched]);

  // 3. Top Under-Forecasting Outliers (Actual >> Forecast)
  const topUnderForecasts = useMemo(() => {
    return [...matched]
      .filter((i) => i.signedError < 0)
      .sort((a, b) => a.signedError - b.signedError)
      .slice(0, 4);
  }, [matched]);

  if (!matched.length) {
    return (
      <div className="card bg-base-100 border border-base-300 p-8 text-center text-base-content/60">
        No matched error data available for analysis.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Signed Error Over Time Timeline */}
      <div className="card bg-base-100 border border-base-300 shadow-sm p-4 lg:p-6 space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-base-300 pb-3">
          <div>
            <h3 className="text-base font-bold text-base-content flex items-center gap-2">
              <Activity className="w-4 h-4 text-primary" />
              Signed Forecast Error Over Time (Forecast − Actual)
            </h3>
            <p className="text-xs text-base-content/60">
              Positive values (above zero) indicate over-forecasting; negative values indicate under-forecasting.
            </p>
          </div>
          <div className="flex items-center gap-3 text-xs">
            <span className="flex items-center gap-1.5 text-warning font-semibold">
              <span className="w-2.5 h-2.5 rounded-full bg-warning inline-block"></span>
              Over-Forecast (&gt; 0 MW)
            </span>
            <span className="flex items-center gap-1.5 text-info font-semibold">
              <span className="w-2.5 h-2.5 rounded-full bg-info inline-block"></span>
              Under-Forecast (&lt; 0 MW)
            </span>
          </div>
        </div>

        <div className="w-full h-80">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={matched} margin={{ top: 15, right: 15, bottom: 5, left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="currentColor" className="text-base-300" opacity={0.5} />
              <XAxis
                dataKey="startTime"
                tickFormatter={(val) => formatIsoTime(val)}
                tick={{ fontSize: 11, fill: 'currentColor' }}
                className="text-base-content/60"
                minTickGap={25}
              />
              <YAxis
                unit=" MW"
                tick={{ fontSize: 11, fill: 'currentColor' }}
                className="text-base-content/60"
              />
              <Tooltip content={<ErrorTimelineTooltip />} />
              <ReferenceLine y={0} stroke="#94a3b8" strokeWidth={1.5} />
              <Bar dataKey="signedError">
                {matched.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={entry.signedError >= 0 ? '#f59e0b' : '#0284c7'}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Diurnal Error Profile & Extreme Outliers Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Diurnal 24-Hour Profile */}
        <div className="card bg-base-100 border border-base-300 shadow-sm p-4 lg:p-6 space-y-3">
          <div className="border-b border-base-300 pb-2.5">
            <h3 className="text-sm font-bold text-base-content flex items-center gap-2">
              <Clock className="w-4 h-4 text-primary" />
              Diurnal Bias Profile (Average Error by Hour of Day)
            </h3>
            <p className="text-[11px] text-base-content/60">
              Reveals time-of-day bias across GB settlement periods (00:00 to 23:00 UTC)
            </p>
          </div>

          <div className="w-full h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={diurnalData} margin={{ top: 10, right: 10, bottom: 10, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="currentColor" className="text-base-300" opacity={0.5} />
                <XAxis
                  dataKey="label"
                  tick={{ fontSize: 10, fill: 'currentColor' }}
                  className="text-base-content/60"
                  interval={2}
                />
                <YAxis
                  unit=" MW"
                  tick={{ fontSize: 10, fill: 'currentColor' }}
                  className="text-base-content/60"
                />
                <Tooltip
                  formatter={(val) => [`${formatNumber(val)} MW`, 'Avg Signed Bias']}
                  contentStyle={{
                    backgroundColor: 'oklch(21% 0.02 245)',
                    border: '1px solid oklch(27% 0.025 245)',
                    borderRadius: '8px',
                    fontSize: '11px',
                    color: '#f8fafc',
                  }}
                />
                <ReferenceLine y={0} stroke="#94a3b8" />
                <Bar dataKey="avgError" radius={[3, 3, 0, 0]}>
                  {diurnalData.map((entry, index) => (
                    <Cell
                      key={`diurnal-${index}`}
                      fill={entry.avgError >= 0 ? '#fbbf24' : '#38bdf8'}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Extreme Deviation Outliers */}
        <div className="card bg-base-100 border border-base-300 shadow-sm p-4 lg:p-6 space-y-4">
          <div className="border-b border-base-300 pb-2.5">
            <h3 className="text-sm font-bold text-base-content flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-warning" />
              Extreme Forecast Deviations
            </h3>
            <p className="text-[11px] text-base-content/60">
              Largest individual over-forecast and under-forecast intervals
            </p>
          </div>

          {/* Top Over-Forecasts */}
          <div className="space-y-2">
            <div className="text-[11px] font-bold uppercase tracking-wider text-warning flex items-center gap-1.5">
              <ArrowUpRight className="w-3.5 h-3.5" />
              Top Over-Forecast Intervals (Forecast &gt; Actual)
            </div>
            <div className="space-y-1.5">
              {topOverForecasts.map((item, idx) => (
                <div
                  key={`over-${idx}`}
                  className="p-2 rounded bg-base-200/80 border border-base-300 flex items-center justify-between text-xs font-mono"
                >
                  <div>
                    <span className="font-semibold text-base-content">
                      {formatIsoTime(item.startTime)}
                    </span>
                    <span className="text-base-content/50 ml-2">
                      ACT: {formatMW(item.actualGeneration)} | FC: {formatMW(item.forecastGeneration)}
                    </span>
                  </div>
                  <div className="font-bold text-warning">
                    +{formatNumber(item.signedError)} MW
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Top Under-Forecasts */}
          <div className="space-y-2 pt-2 border-t border-base-200">
            <div className="text-[11px] font-bold uppercase tracking-wider text-info flex items-center gap-1.5">
              <ArrowDownRight className="w-3.5 h-3.5" />
              Top Under-Forecast Intervals (Actual &gt; Forecast)
            </div>
            <div className="space-y-1.5">
              {topUnderForecasts.map((item, idx) => (
                <div
                  key={`under-${idx}`}
                  className="p-2 rounded bg-base-200/80 border border-base-300 flex items-center justify-between text-xs font-mono"
                >
                  <div>
                    <span className="font-semibold text-base-content">
                      {formatIsoTime(item.startTime)}
                    </span>
                    <span className="text-base-content/50 ml-2">
                      ACT: {formatMW(item.actualGeneration)} | FC: {formatMW(item.forecastGeneration)}
                    </span>
                  </div>
                  <div className="font-bold text-info">
                    {formatNumber(item.signedError)} MW
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

