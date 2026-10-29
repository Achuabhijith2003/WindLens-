import React, { useMemo } from 'react';
import {
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  BarChart,
  Bar,
  Cell,
  Legend,
} from 'recharts';
import { formatMW, formatNumber, formatPercent, formatIsoTime, formatIsoDateTime } from '../utils/formatters';
import { Crosshair, BarChart2, TrendingUp, Compass, Activity } from 'lucide-react';

function ScatterTooltip({ active, payload }) {
  if (!active || !payload || !payload.length) return null;
  const data = payload[0]?.payload || {};

  return (
    <div className="bg-base-100/95 backdrop-blur border border-base-300 rounded-lg p-3 shadow-xl text-xs space-y-1 z-50">
      <div className="font-bold border-b border-base-300 pb-1 text-base-content flex justify-between items-center">
        <span>{data.time ? formatIsoDateTime(data.time) : 'Interval'}</span>
        {data.signedError > 0 ? (
          <span className="badge badge-xs badge-warning text-warning-content">Over-forecast</span>
        ) : data.signedError < 0 ? (
          <span className="badge badge-xs badge-info text-info-content">Under-forecast</span>
        ) : (
          <span className="badge badge-xs badge-neutral">Exact</span>
        )}
      </div>
      <div className="flex justify-between gap-4 pt-1 text-secondary">
        <span>Actual Outturn:</span>
        <span className="font-mono font-bold">{formatMW(data.actual)}</span>
      </div>
      <div className="flex justify-between gap-4 text-primary">
        <span>Forecast:</span>
        <span className="font-mono font-bold">{formatMW(data.forecast)}</span>
      </div>
      <div className="flex justify-between gap-4 pt-1 border-t border-base-200 text-base-content/80">
        <span>Deviation (FC - ACT):</span>
        <span className="font-mono font-bold">
          {data.signedError > 0 ? `+${formatNumber(data.signedError)}` : formatNumber(data.signedError)} MW
        </span>
      </div>
    </div>
  );
}

export default function ForecastAnalysisTab({ intervals = [], metrics = null, resolution = 'hourly' }) {
  // 1. Prepare Matched Datasets
  const matched = useMemo(() => {
    return intervals.filter(
      (i) => i.actualGeneration !== null && i.forecastGeneration !== null
    );
  }, [intervals]);

  // 2. Correlation Statistics & Scatter Points
  const { scatterData, maxVal, correlationR2, correlationR } = useMemo(() => {
    if (!matched.length) {
      return { scatterData: [], maxVal: 20000, correlationR2: null, correlationR: null };
    }

    let maxG = 0;
    let sumX = 0;
    let sumY = 0;

    const data = matched.map((i) => {
      const act = i.actualGeneration;
      const fc = i.forecastGeneration;
      if (act > maxG) maxG = act;
      if (fc > maxG) maxG = fc;
      sumX += act;
      sumY += fc;
      return {
        actual: act,
        forecast: fc,
        signedError: i.signedError,
        time: i.startTime,
      };
    });

    // Pearson Correlation
    const n = matched.length;
    const meanX = sumX / n;
    const meanY = sumY / n;

    let num = 0;
    let denX = 0;
    let denY = 0;

    matched.forEach((i) => {
      const dx = i.actualGeneration - meanX;
      const dy = i.forecastGeneration - meanY;
      num += dx * dy;
      denX += dx * dx;
      denY += dy * dy;
    });

    let r = 0;
    if (denX > 0 && denY > 0) {
      r = num / Math.sqrt(denX * denY);
    }
    const r2 = r * r;

    // Add 10% ceiling buffer for clean 1:1 reference line
    const ceilMax = Math.ceil((maxG * 1.08) / 1000) * 1000;

    return {
      scatterData: data,
      maxVal: Math.max(ceilMax, 1000),
      correlationR2: Number.isFinite(r2) ? r2 : null,
      correlationR: Number.isFinite(r) ? r : null,
    };
  }, [matched]);

  // 3. Error Distribution Histogram Bins
  const histogramData = useMemo(() => {
    if (!matched.length) return [];

    // Define 6 symmetrical error bins (MW)
    const bins = [
      { range: '< -2000', label: 'Severe Under', min: -Infinity, max: -2000, count: 0, color: '#0284c7' },
      { range: '-2000 to -1000', label: 'Mod Under', min: -2000, max: -1000, count: 0, color: '#38bdf8' },
      { range: '-1000 to 0', label: 'Slight Under', min: -1000, max: 0, count: 0, color: '#7dd3fc' },
      { range: '0 to +1000', label: 'Slight Over', min: 0, max: 1000, count: 0, color: '#fde047' },
      { range: '+1000 to +2000', label: 'Mod Over', min: 1000, max: 2000, count: 0, color: '#fbbf24' },
      { range: '> +2000', label: 'Severe Over', min: 2000, max: Infinity, count: 0, color: '#f97316' },
    ];

    matched.forEach((item) => {
      const err = item.signedError;
      if (err !== null && err !== undefined) {
        for (const b of bins) {
          if (err >= b.min && err < b.max) {
            b.count += 1;
            break;
          }
          if (b.max === Infinity && err >= b.min) {
            b.count += 1;
            break;
          }
        }
      }
    });

    return bins.map((b) => ({
      ...b,
      pct: ((b.count / matched.length) * 100).toFixed(1),
    }));
  }, [matched]);

  // 4. Generation Percentiles
  const percentiles = useMemo(() => {
    if (!matched.length) return null;
    const sortedActuals = [...matched.map((i) => i.actualGeneration)].sort((a, b) => a - b);
    const sortedForecasts = [...matched.map((i) => i.forecastGeneration)].sort((a, b) => a - b);

    const getP = (arr, p) => arr[Math.floor(arr.length * p)] || 0;

    return {
      actualP10: getP(sortedActuals, 0.1),
      actualP50: getP(sortedActuals, 0.5),
      actualP90: getP(sortedActuals, 0.9),
      forecastP10: getP(sortedForecasts, 0.1),
      forecastP50: getP(sortedForecasts, 0.5),
      forecastP90: getP(sortedForecasts, 0.9),
    };
  }, [matched]);

  if (!matched.length) {
    return (
      <div className="card bg-base-100 border border-base-300 p-8 text-center text-base-content/60">
        No matched forecast/actual generation data available for correlation analysis.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Correlation Overview Banner */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="card bg-base-100 border border-base-300 p-3.5 shadow-xs">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-base-content/60 flex items-center justify-between">
            <span>Pearson Correlation (r)</span>
            <Compass className="w-3.5 h-3.5 text-primary" />
          </div>
          <div className="text-xl font-bold font-mono text-base-content mt-1">
            {correlationR !== null ? correlationR.toFixed(3) : '—'}
          </div>
          <div className="text-[11px] text-base-content/60 mt-0.5">
            {correlationR !== null && correlationR > 0.8
              ? 'Strong linear relationship'
              : 'Moderate linear correlation'}
          </div>
        </div>

        <div className="card bg-base-100 border border-base-300 p-3.5 shadow-xs">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-base-content/60 flex items-center justify-between">
            <span>Coefficient of Det. (R²)</span>
            <TrendingUp className="w-3.5 h-3.5 text-secondary" />
          </div>
          <div className="text-xl font-bold font-mono text-base-content mt-1">
            {correlationR2 !== null ? correlationR2.toFixed(3) : '—'}
          </div>
          <div className="text-[11px] text-base-content/60 mt-0.5">
            Variance explained by forecast
          </div>
        </div>

        <div className="card bg-base-100 border border-base-300 p-3.5 shadow-xs">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-base-content/60 flex items-center justify-between">
            <span>Actual Outturn P50</span>
            <Activity className="w-3.5 h-3.5 text-secondary" />
          </div>
          <div className="text-xl font-bold font-mono text-base-content mt-1">
            {percentiles ? formatMW(percentiles.actualP50) : '—'}
          </div>
          <div className="text-[11px] text-base-content/60 mt-0.5">
            P10: {percentiles ? formatMW(percentiles.actualP10) : '—'} | P90: {percentiles ? formatMW(percentiles.actualP90) : '—'}
          </div>
        </div>

        <div className="card bg-base-100 border border-base-300 p-3.5 shadow-xs">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-base-content/60 flex items-center justify-between">
            <span>Forecast P50</span>
            <Activity className="w-3.5 h-3.5 text-primary" />
          </div>
          <div className="text-xl font-bold font-mono text-base-content mt-1">
            {percentiles ? formatMW(percentiles.forecastP50) : '—'}
          </div>
          <div className="text-[11px] text-base-content/60 mt-0.5">
            P10: {percentiles ? formatMW(percentiles.forecastP10) : '—'} | P90: {percentiles ? formatMW(percentiles.forecastP90) : '—'}
          </div>
        </div>
      </div>

      {/* Two Column Analysis: Scatter Plot & Histogram */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Actual vs Forecast Scatter Correlation */}
        <div className="card bg-base-100 border border-base-300 shadow-sm p-4 lg:p-6 space-y-3">
          <div className="flex items-center justify-between border-b border-base-300 pb-2.5">
            <div>
              <h3 className="text-sm font-bold text-base-content flex items-center gap-2">
                <Crosshair className="w-4 h-4 text-primary" />
                Actual vs Forecast Correlation (y = x)
              </h3>
              <p className="text-[11px] text-base-content/60">
                Points above 1:1 line = Over-forecast; below line = Under-forecast
              </p>
            </div>
            <div className="badge badge-sm badge-neutral font-mono text-[10px]">
              {matched.length} intervals
            </div>
          </div>

          <div className="w-full h-72">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 15, right: 20, bottom: 20, left: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="currentColor" className="text-base-300" opacity={0.5} />
                <XAxis
                  type="number"
                  dataKey="actual"
                  name="Actual Outturn (MW)"
                  unit=" MW"
                  domain={[0, maxVal]}
                  tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
                  tick={{ fontSize: 11, fill: 'currentColor' }}
                  className="text-base-content/60"
                  label={{ value: 'Actual FUELHH Outturn (MW)', position: 'insideBottom', offset: -10, fontSize: 11, fill: 'currentColor' }}
                />
                <YAxis
                  type="number"
                  dataKey="forecast"
                  name="WINDFOR Forecast (MW)"
                  unit=" MW"
                  domain={[0, maxVal]}
                  tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
                  tick={{ fontSize: 11, fill: 'currentColor' }}
                  className="text-base-content/60"
                  label={{ value: 'WINDFOR Forecast (MW)', angle: -90, position: 'insideLeft', offset: 5, fontSize: 11, fill: 'currentColor' }}
                />
                <Tooltip content={<ScatterTooltip />} />
                {/* 1:1 Reference Diagonal Line */}
                <ReferenceLine
                  segment={[
                    { x: 0, y: 0 },
                    { x: maxVal, y: maxVal },
                  ]}
                  stroke="#94a3b8"
                  strokeDasharray="4 4"
                  strokeWidth={1.5}
                />
                <Scatter
                  name="Delivery Intervals"
                  data={scatterData}
                  fill="#38bdf8"
                  opacity={0.8}
                />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Forecast Error Distribution Histogram */}
        <div className="card bg-base-100 border border-base-300 shadow-sm p-4 lg:p-6 space-y-3">
          <div className="flex items-center justify-between border-b border-base-300 pb-2.5">
            <div>
              <h3 className="text-sm font-bold text-base-content flex items-center gap-2">
                <BarChart2 className="w-4 h-4 text-warning" />
                Forecast Error Distribution (MW)
              </h3>
              <p className="text-[11px] text-base-content/60">
                Frequency count binned by signed error = Forecast - Actual (MW)
              </p>
            </div>
          </div>

          <div className="w-full h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={histogramData} margin={{ top: 15, right: 15, bottom: 25, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="currentColor" className="text-base-300" opacity={0.5} />
                <XAxis
                  dataKey="range"
                  tick={{ fontSize: 10, fill: 'currentColor' }}
                  className="text-base-content/60"
                  interval={0}
                  angle={-18}
                  textAnchor="end"
                />
                <YAxis
                  tick={{ fontSize: 11, fill: 'currentColor' }}
                  className="text-base-content/60"
                  allowDecimals={false}
                />
                <Tooltip
                  formatter={(val, name, item) => [
                    `${val} intervals (${item.payload.pct}%)`,
                    item.payload.label,
                  ]}
                  contentStyle={{
                    backgroundColor: 'oklch(21% 0.02 245)',
                    border: '1px solid oklch(27% 0.025 245)',
                    borderRadius: '8px',
                    fontSize: '11px',
                    color: '#f8fafc',
                  }}
                />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {histogramData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}

