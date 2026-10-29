import React, { useState, useMemo } from 'react';
import { Download, Search, ArrowUpDown, ChevronLeft, ChevronRight } from 'lucide-react';
import { formatIsoDateTime, formatIsoTime, formatNumber, formatMW } from '../utils/formatters';
import { exportIntervalsToCsv } from '../utils/exportCsv';

export default function IntervalTable({
  intervals = [],
  metadata = {},
  resolution = 'hourly',
}) {
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortField, setSortField] = useState('startTime');
  const [sortDirection, setSortDirection] = useState('asc'); // 'asc' or 'desc'
  const [pageSize, setPageSize] = useState(24);
  const [currentPage, setCurrentPage] = useState(1);

  // Toggle sort field & direction
  const handleSort = (field) => {
    if (sortField === field) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  // Filter logic
  const filtered = useMemo(() => {
    return intervals.filter((item) => {
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
  }, [intervals, statusFilter, searchQuery]);

  // Sort logic
  const sorted = useMemo(() => {
    const list = [...filtered];
    list.sort((a, b) => {
      let valA = a[sortField];
      let valB = b[sortField];

      // Handle nulls
      if (valA === null || valA === undefined) return 1;
      if (valB === null || valB === undefined) return -1;

      if (typeof valA === 'string') {
        const cmp = valA.localeCompare(valB);
        return sortDirection === 'asc' ? cmp : -cmp;
      }

      return sortDirection === 'asc' ? valA - valB : valB - valA;
    });
    return list;
  }, [filtered, sortField, sortDirection]);

  // Pagination logic
  const totalItems = sorted.length;
  const effectivePageSize = pageSize === 'ALL' ? totalItems || 1 : Number(pageSize);
  const totalPages = Math.max(1, Math.ceil(totalItems / effectivePageSize));
  const page = Math.min(currentPage, totalPages);

  const paginatedData = useMemo(() => {
    if (pageSize === 'ALL') return sorted;
    const start = (page - 1) * effectivePageSize;
    return sorted.slice(start, start + effectivePageSize);
  }, [sorted, page, effectivePageSize, pageSize]);

  return (
    <div className="card bg-base-100 border border-base-300 shadow-sm p-4 lg:p-6 space-y-4">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-base-300 pb-3">
        <div>
          <h2 className="text-base font-bold text-base-content tracking-tight">
            Detailed Delivery Intervals
          </h2>
          <p className="text-xs text-base-content/60">
            Showing {paginatedData.length} of {intervals.length} delivery periods ({resolution})
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {/* Status filter */}
          <div className="join">
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setCurrentPage(1);
              }}
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
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setCurrentPage(1);
              }}
              className="input input-xs input-bordered pl-7 pr-2 font-mono text-xs w-36"
            />
            <Search className="w-3.5 h-3.5 text-base-content/40 absolute left-2 top-2" />
          </div>

          {/* Page size toggle buttons */}
          <div className="join" title="Rows per page">
            {[12, 24, 48].map((size) => (
              <button
                key={size}
                type="button"
                onClick={() => {
                  setPageSize(size);
                  setCurrentPage(1);
                }}
                className={`btn btn-xs join-item border-base-300 ${
                  pageSize === size ? 'btn-active bg-base-300 text-base-content font-bold' : ''
                }`}
              >
                {size}
              </button>
            ))}
            <button
              type="button"
              onClick={() => {
                setPageSize('ALL');
                setCurrentPage(1);
              }}
              className={`btn btn-xs join-item border-base-300 ${
                pageSize === 'ALL' ? 'btn-active bg-base-300 text-base-content font-bold' : ''
              }`}
            >
              All
            </button>
          </div>

          {/* CSV Export Button */}
          <button
            type="button"
            onClick={() => exportIntervalsToCsv(sorted, metadata)}
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
            <tr className="bg-base-200 text-base-content/80 uppercase text-[10px] tracking-wider font-sans select-none">
              <th
                onClick={() => handleSort('startTime')}
                className="cursor-pointer hover:text-base-content"
              >
                <div className="flex items-center gap-1">
                  <span>Delivery Start (UTC)</span>
                  <ArrowUpDown className="w-2.5 h-2.5 opacity-60" />
                </div>
              </th>
              <th className="text-center">SP</th>
              <th
                onClick={() => handleSort('forecastGeneration')}
                className="text-right cursor-pointer hover:text-base-content"
              >
                <div className="flex items-center justify-end gap-1">
                  <span>Forecast</span>
                  <ArrowUpDown className="w-2.5 h-2.5 opacity-60" />
                </div>
              </th>
              <th
                onClick={() => handleSort('actualGeneration')}
                className="text-right cursor-pointer hover:text-base-content"
              >
                <div className="flex items-center justify-end gap-1">
                  <span>Actual</span>
                  <ArrowUpDown className="w-2.5 h-2.5 opacity-60" />
                </div>
              </th>
              <th
                onClick={() => handleSort('signedError')}
                className="text-right cursor-pointer hover:text-base-content"
              >
                <div className="flex items-center justify-end gap-1">
                  <span>Signed Error</span>
                  <ArrowUpDown className="w-2.5 h-2.5 opacity-60" />
                </div>
              </th>
              <th className="text-center">Status</th>
              <th>Forecast Published (UTC)</th>
              <th
                onClick={() => handleSort('leadTimeHours')}
                className="text-right cursor-pointer hover:text-base-content"
              >
                <div className="flex items-center justify-end gap-1">
                  <span>Lead Time</span>
                  <ArrowUpDown className="w-2.5 h-2.5 opacity-60" />
                </div>
              </th>
            </tr>
          </thead>
          <tbody>
            {paginatedData.length === 0 ? (
              <tr>
                <td colSpan={8} className="text-center py-8 text-base-content/50 font-sans">
                  No delivery intervals match the selected filters.
                </td>
              </tr>
            ) : (
              paginatedData.map((item, idx) => {
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

      {/* Pagination Bar */}
      {pageSize !== 'ALL' && totalPages > 1 && (
        <div className="flex items-center justify-between text-xs text-base-content/70 pt-2 border-t border-base-200">
          <div>
            Showing {(page - 1) * effectivePageSize + 1} to{' '}
            {Math.min(page * effectivePageSize, totalItems)} of {totalItems} rows
          </div>
          <div className="join">
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="btn btn-xs join-item border-base-300"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>
            <span className="btn btn-xs join-item border-base-300 pointer-events-none font-mono">
              Page {page} / {totalPages}
            </span>
            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="btn btn-xs join-item border-base-300"
            >
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
