import React, { useState, useEffect, useCallback } from 'react';
import Header from './components/Header';
import FilterPanel from './components/FilterPanel';
import KpiCards from './components/KpiCards';
import ForecastChart from './components/ForecastChart';
import DataQualitySection from './components/DataQualitySection';
import IntervalTable from './components/IntervalTable';
import { apiService } from './services/api';
import { AlertTriangle, RefreshCw, BarChart3, Database } from 'lucide-react';

export default function App() {
  const [deliveryDate, setDeliveryDate] = useState('2026-01-01');
  const [cutoff, setCutoff] = useState('day_ahead_1700');
  const [resolution, setResolution] = useState('hourly');
  const [rangeMode, setRangeMode] = useState(false);
  const [fromDate, setFromDate] = useState('2026-01-01');
  const [toDate, setToDate] = useState('2026-01-03');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isConnected, setIsConnected] = useState(true);

  const [overviewData, setOverviewData] = useState(null);
  const [timeseriesData, setTimeseriesData] = useState(null);
  const [accuracyData, setAccuracyData] = useState(null);

  // Health check on initial load
  useEffect(() => {
    apiService
      .checkHealth()
      .then(() => setIsConnected(true))
      .catch(() => setIsConnected(false));
  }, []);

  // Main data fetching logic
  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      if (!rangeMode) {
        // Single day mode: fetch overview & timeseries in parallel
        const [overviewRes, timeseriesRes] = await Promise.all([
          apiService.getOverview(deliveryDate, cutoff, resolution),
          apiService.getTimeseries(deliveryDate, cutoff, resolution),
        ]);
        setOverviewData(overviewRes);
        setTimeseriesData(timeseriesRes);
        setAccuracyData(null);
        setIsConnected(true);
      } else {
        // Multi-day range mode: fetch accuracy range
        const accuracyRes = await apiService.getAccuracy(fromDate, toDate, cutoff, resolution);
        setAccuracyData(accuracyRes);
        setOverviewData(null);
        setTimeseriesData(null);
        setIsConnected(true);
      }
    } catch (err) {
      console.error('WindLens API fetch error:', err);
      setError(err.message || 'Failed to fetch data from WindLens backend.');
      setIsConnected(false);
    } finally {
      setLoading(false);
    }
  }, [deliveryDate, cutoff, resolution, rangeMode, fromDate, toDate]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Active metrics & intervals to display
  const activeMetrics = rangeMode ? accuracyData?.metrics : overviewData?.metrics;
  const activeDiagnostics = rangeMode ? accuracyData?.diagnostics : timeseriesData?.diagnostics;
  const activeIntervals = timeseriesData?.intervals || [];

  return (
    <div className="min-h-screen bg-base-200 text-base-content flex flex-col">
      <Header isConnected={isConnected} />

      <main className="flex-1 max-w-7xl w-full mx-auto p-4 lg:p-6 space-y-6">
        {/* Controls / Filter Panel */}
        <FilterPanel
          deliveryDate={deliveryDate}
          onDateChange={setDeliveryDate}
          cutoff={cutoff}
          onCutoffChange={setCutoff}
          resolution={resolution}
          onResolutionChange={setResolution}
          rangeMode={rangeMode}
          onRangeModeToggle={() => setRangeMode(!rangeMode)}
          fromDate={fromDate}
          onFromDateChange={setFromDate}
          toDate={toDate}
          onToDateChange={setToDate}
          onRefresh={loadData}
          loading={loading}
        />

        {/* Error Notification */}
        {error && (
          <div role="alert" className="alert alert-error shadow-sm text-sm">
            <AlertTriangle className="w-5 h-5 shrink-0" />
            <div className="flex-1">
              <span className="font-bold">Backend Communication Error:</span>
              <span className="ml-1.5">{error}</span>
            </div>
            <button
              onClick={loadData}
              className="btn btn-xs btn-outline btn-ghost"
              disabled={loading}
            >
              Retry
            </button>
          </div>
        )}

        {/* Loading indicator */}
        {loading && !overviewData && !accuracyData && (
          <div className="card bg-base-100 border border-base-300 p-12 text-center shadow-sm space-y-3">
            <span className="loading loading-spinner loading-lg text-primary mx-auto"></span>
            <p className="text-sm font-semibold text-base-content/70">
              Querying Elexon streams and calculating forecast metrics...
            </p>
          </div>
        )}

        {/* Main Dashboard Content */}
        {(!rangeMode && overviewData && timeseriesData) || (rangeMode && accuracyData) ? (
          <div className="space-y-6 animate-fade-in">
            {/* KPI Cards */}
            <KpiCards metrics={activeMetrics} resolution={resolution} />

            {/* If Single Day: Show Chart & Table */}
            {!rangeMode && (
              <>
                <ForecastChart
                  intervals={activeIntervals}
                  resolution={resolution}
                />

                <DataQualitySection
                  diagnostics={activeDiagnostics}
                  metrics={activeMetrics}
                  resolution={resolution}
                />

                <IntervalTable
                  intervals={activeIntervals}
                  metadata={{
                    date: deliveryDate,
                    cutoff: cutoff,
                    resolution: resolution,
                  }}
                  resolution={resolution}
                />
              </>
            )}

            {/* If Multi-Day Range: Show Daily Breakdown Table & Quality Diagnostics */}
            {rangeMode && accuracyData && (
              <>
                <DataQualitySection
                  diagnostics={activeDiagnostics}
                  metrics={activeMetrics}
                  resolution={resolution}
                />

                <div className="card bg-base-100 border border-base-300 shadow-sm p-4 lg:p-6 space-y-4">
                  <div className="flex items-center justify-between border-b border-base-300 pb-3">
                    <div>
                      <h2 className="text-base font-bold text-base-content tracking-tight">
                        Daily Accuracy Breakdown ({accuracyData.fromDate} to {accuracyData.toDate})
                      </h2>
                      <p className="text-xs text-base-content/60">
                        Evaluated under decision cutoff: <strong className="font-mono">{accuracyData.cutoff}</strong> ({resolution})
                      </p>
                    </div>
                  </div>

                  <div className="overflow-x-auto rounded-lg border border-base-200">
                    <table className="table table-sm table-zebra w-full text-xs font-mono">
                      <thead>
                        <tr className="bg-base-200 text-base-content/80 uppercase text-[10px] tracking-wider font-sans">
                          <th>Date</th>
                          <th className="text-right">MAE (MW)</th>
                          <th className="text-right">RMSE (MW)</th>
                          <th className="text-right">Signed Bias (MW)</th>
                          <th className="text-right">MAPE (%)</th>
                          <th className="text-center">Matched / Expected</th>
                          <th className="text-center">Completeness</th>
                        </tr>
                      </thead>
                      <tbody>
                        {accuracyData.dailyBreakdown.map((day) => (
                          <tr key={day.date} className="hover">
                            <td className="font-semibold text-base-content">{day.date}</td>
                            <td className="text-right font-semibold text-primary">
                              {day.metrics.mae_mw !== null ? `${day.metrics.mae_mw} MW` : '—'}
                            </td>
                            <td className="text-right font-semibold">
                              {day.metrics.rmse_mw !== null ? `${day.metrics.rmse_mw} MW` : '—'}
                            </td>
                            <td className="text-right font-bold">
                              {day.metrics.signed_bias_mw !== null ? (
                                <span className={day.metrics.signed_bias_mw > 0 ? 'text-warning' : 'text-info'}>
                                  {day.metrics.signed_bias_mw > 0 ? `+${day.metrics.signed_bias_mw}` : day.metrics.signed_bias_mw} MW
                                </span>
                              ) : (
                                '—'
                              )}
                            </td>
                            <td className="text-right">
                              {day.metrics.mape_pct !== null ? `${day.metrics.mape_pct}%` : '—'}
                            </td>
                            <td className="text-center">
                              {day.matchedCount} / {day.expectedCount}
                            </td>
                            <td className="text-center">
                              <span className="badge badge-xs badge-neutral">
                                {day.metrics.data_completeness_pct}%
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </>
            )}
          </div>
        ) : null}
      </main>

      <footer className="footer footer-center p-4 bg-base-100 text-base-content/60 text-xs border-t border-base-300">
        <div>
          <p>WindLens UK Energy Analytics &copy; 2026. Data sourced from Elexon BMRS Insights API (FUELHH & WINDFOR streams).</p>
        </div>
      </footer>
    </div>
  );
}

