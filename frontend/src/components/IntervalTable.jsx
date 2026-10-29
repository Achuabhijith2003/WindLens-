import React, { useState } from 'react';
import { Download, Search, Filter } from 'lucide-react';
import { formatIsoDateTime, formatIsoTime, formatNumber, formatMW } from '../utils/formatters';
import { exportIntervalsToCsv } from '../utils/exportCsv';

export default function IntervalTable({
  intervals = [],
  metadata = {},
  resolution = 'hourly',
}) {
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  const filtered = intervals.filter((item) => {
    if (statusFilter !== 'ALL' && item.status !== statusFilter) {
      return false;
    }
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      const matchTime = item.startTime?.toLowerCase().includes(q);
      const matchSp = String(item.settlementPeriod).includes(q);
      const matchStatus = item.status?.toLowerCase().includes(q);
      if (!matchTime && !matchSp && !matchStatus) return false;
    }
    return true;
  });

  return (
    <div className="card bg-base-100 border border-base-300 shadow-sm p-4 lg:p-6 space-y-4">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-base-300 pb-3">
        <div>
          <h2 className="text-base font-bold text-base-content tracking-tight">
            Detailed Delivery Intervals
          </h2>
          <p className="text-xs text-base-content/60">
            Showing {filtered.length} of {intervals.length} delivery periods ({resolution})
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {/* Status filter */}
          <div className="join">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="select select-xs select-bordered join-item text-xs"
            >
              <option value="ALL">All Statuses</option>
              <option value="matched">Matched Only</option>
              <option value="resolution_mismatch">Resolution Mismatch (:30)</option>
              <option value="missing_forecast">Missing Forecast</option>
              <option value="missing_actual">Missing Actual</option>
            </select>
          </div>

          {/* Search box */}
          <div className="relative">
            <input
              type="text"
              placeholder="Search time or SP..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="input input-xs input-bordered pl-7 pr-2 font-mono text-xs w-36"
            />
            <Search className="w-3.5 h-3.5 text-base-content/40 absolute left-2 top-2" />
          </div>

          {/* CSV Export Button */}
          <button
            type="button"
            onClick={() => exportIntervalsToCsv(intervals, metadata)}
            className="btn btn-xs btn-outline border-base-300 gap-1.5"
            title="Download CSV of displayed comparison intervals"
          >
            <Download className="w-3 h-3 text-primary" />
            Export CSV
          </button>
        </div>
      </div>

      {/* Table Content */}
      <div className="overflow-x-auto max-h-96 rounded-lg border border-base-200">
        <table className="table table-xs table-pin-rows table-zebra w-full text-xs font-mono">
          <thead>
            <tr className="bg-base-200 text-base-content/80 uppercase text-[10px] tracking-wider font-sans">
              <th>Delivery Start (UTC)</th>
              <th className="text-center">SP</th>
              <th className="text-right">Forecast</th>
              <th className="text-right">Actual</th>
              <th className="text-right">Signed Error</th>
              <th className="text-center">Status</th>
              <th>Forecast Published (UTC)</th>
              <th className="text-right">Lead Time</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={8} className="text-center py-8 text-base-content/50 font-sans">
                  No delivery intervals match the selected filters.
                </td>
              </tr>
            ) : (
              filtered.map((item, idx) => {
                const signedErr = item.signedError;
                const errColor =
                  signedErr === null || signedErr === undefined
                    ? 'text-base-content/40'
                    : signedErr > 0
                    ? 'text-warning'
                    : signedErr < 0
                    ? 'text-info'
                    : 'text-base-content/80';

                return (
                  <tr key={item.startTime || idx} className="hover">
                    <td className="font-semibold text-base-content whitespace-nowrap">
                      {formatIsoDateTime(item.startTime)}
                    </td>
                    <td className="text-center">
                      {item.settlementPeriod ? (
                        <span className="badge badge-xs badge-neutral">{item.settlementPeriod}</span>
                      ) : (
                        '—'
                      )}
                    </td>
                    <td className="text-right font-semibold text-primary">
                      {item.forecastGeneration !== null && item.forecastGeneration !== undefined
                        ? formatNumber(item.forecastGeneration)
                        : '—'}
                    </td>
                    <td className="text-right font-semibold text-success">
                      {item.actualGeneration !== null && item.actualGeneration !== undefined
                        ? formatNumber(item.actualGeneration)
                        : '—'}
                    </td>
                    <td className={`text-right font-bold ${errColor}`}>
                      {signedErr !== null && signedErr !== undefined
                        ? signedErr > 0
                          ? `+${formatNumber(signedErr)}`
                          : formatNumber(signedErr)
                        : '—'}
                    </td>
                    <td className="text-center">
                      <span
                        className={`badge badge-xs ${
                          item.status === 'matched'
                            ? 'badge-success'
                            : item.status === 'resolution_mismatch'
                            ? 'badge-warning'
                            : 'badge-error'
                        }`}
                      >
                        {item.status === 'resolution_mismatch' ? 'mismatch (:30)' : item.status}
                      </span>
                    </td>
                    <td className="text-base-content/70 whitespace-nowrap">
                      {item.forecastPublishTime ? formatIsoTime(item.forecastPublishTime) : '—'}
                    </td>
                    <td className="text-right text-base-content/70">
                      {item.leadTimeHours !== null && item.leadTimeHours !== undefined
                        ? `${formatNumber(item.leadTimeHours)}h`
                        : '—'}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

