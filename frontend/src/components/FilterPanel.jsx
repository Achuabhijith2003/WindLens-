import React from 'react';
import { Calendar, Filter, RefreshCw, Clock, Layers } from 'lucide-react';

const CUTOFF_OPTIONS = [
  { value: 'day_ahead_1700', label: 'Day-Ahead (D-1 17:00 UTC) - Default' },
  { value: 'day_ahead_1200', label: 'Day-Ahead Auction (D-1 12:00 UTC)' },
  { value: 'gate_closure_1h', label: 'Gate Closure (1h Lead Time)' },
  { value: 'gate_closure_2h', label: 'Gate Closure (2h Lead Time)' },
  { value: 'lead_4h', label: 'Short-Term (4h Lead Time)' },
];

export default function FilterPanel({
  deliveryDate,
  onDateChange,
  cutoff,
  onCutoffChange,
  resolution,
  onResolutionChange,
  rangeMode,
  onRangeModeToggle,
  fromDate,
  onFromDateChange,
  toDate,
  onToDateChange,
  onRefresh,
  loading = false,
}) {
  return (
    <div className="card bg-base-100 border border-base-300 shadow-sm p-4 lg:p-5">
      <div className="flex flex-col lg:flex-row items-stretch lg:items-end justify-between gap-4">
        {/* Filters Group */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5 flex-1">
          {/* Mode: Single Day vs Date Range */}
          {!rangeMode ? (
            <div>
              <label className="label py-1 text-xs font-semibold text-base-content/70">
                <span className="flex items-center gap-1.5">
                  <Calendar className="w-3.5 h-3.5 text-primary" /> Delivery Date
                </span>
              </label>
              <input
                type="date"
                min="2026-01-01"
                max="2026-01-31"
                value={deliveryDate}
                onChange={(e) => onDateChange(e.target.value)}
                className="input input-sm input-bordered w-full font-mono text-sm"
                disabled={loading}
              />
            </div>
          ) : (
            <>
              <div>
                <label className="label py-1 text-xs font-semibold text-base-content/70">
                  <span className="flex items-center gap-1.5">
                    <Calendar className="w-3.5 h-3.5 text-primary" /> From Date
                  </span>
                </label>
                <input
                  type="date"
                  min="2026-01-01"
                  max="2026-01-31"
                  value={fromDate}
                  onChange={(e) => onFromDateChange(e.target.value)}
                  className="input input-sm input-bordered w-full font-mono text-sm"
                  disabled={loading}
                />
              </div>
              <div>
                <label className="label py-1 text-xs font-semibold text-base-content/70">
                  <span className="flex items-center gap-1.5">
                    <Calendar className="w-3.5 h-3.5 text-primary" /> To Date
                  </span>
                </label>
                <input
                  type="date"
                  min="2026-01-01"
                  max="2026-01-31"
                  value={toDate}
                  onChange={(e) => onToDateChange(e.target.value)}
                  className="input input-sm input-bordered w-full font-mono text-sm"
                  disabled={loading}
                />
              </div>
            </>
          )}

          {/* Cutoff Strategy */}
          <div>
            <label className="label py-1 text-xs font-semibold text-base-content/70">
              <span className="flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-primary" /> Decision Cutoff
              </span>
            </label>
            <select
              value={cutoff}
              onChange={(e) => onCutoffChange(e.target.value)}
              className="select select-sm select-bordered w-full text-xs font-medium"
              disabled={loading}
            >
              {CUTOFF_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          {/* Alignment Resolution */}
          <div>
            <label className="label py-1 text-xs font-semibold text-base-content/70">
              <span className="flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-primary" /> Comparison Resolution
              </span>
            </label>
            <div className="join w-full grid grid-cols-2">
              <button
                type="button"
                onClick={() => onResolutionChange('hourly')}
                className={`btn btn-xs join-item ${resolution === 'hourly' ? 'btn-neutral font-bold' : 'btn-outline border-base-300'}`}
                disabled={loading}
              >
                Hourly (24/d)
              </button>
              <button
                type="button"
                onClick={() => onResolutionChange('half_hourly')}
                className={`btn btn-xs join-item ${resolution === 'half_hourly' ? 'btn-neutral font-bold' : 'btn-outline border-base-300'}`}
                disabled={loading}
              >
                Half-Hourly (48/d)
              </button>
            </div>
          </div>
        </div>

        {/* Actions Group */}
        <div className="flex items-center gap-2 pt-2 lg:pt-0">
          <button
            type="button"
            onClick={onRangeModeToggle}
            className="btn btn-sm btn-ghost border border-base-300 text-xs"
            disabled={loading}
          >
            {rangeMode ? 'Single Day View' : 'Multi-Day Range'}
          </button>

          <button
            type="button"
            onClick={onRefresh}
            className="btn btn-sm btn-primary gap-1.5 min-w-[100px]"
            disabled={loading}
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            {loading ? 'Fetching...' : 'Refresh'}
          </button>
        </div>
      </div>
    </div>
  );
}

