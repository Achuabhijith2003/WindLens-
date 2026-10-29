/**
 * CSV export utility for WindLens interval comparisons.
 */

export function exportIntervalsToCsv(intervals, metadata = {}) {
  if (!intervals || !intervals.length) {
    alert('No interval data available to export.');
    return;
  }

  const headers = [
    'startTimeUTC',
    'settlementDate',
    'settlementPeriod',
    'cutoffTimeUTC',
    'forecastGenerationMW',
    'actualGenerationMW',
    'signedErrorMW',
    'absoluteErrorMW',
    'percentageErrorPct',
    'leadTimeHours',
    'status',
    'forecastPublishTimeUTC',
    'actualPublishTimeUTC',
  ];

  const rows = intervals.map((row) => [
    row.startTime || '',
    row.settlementDate || '',
    row.settlementPeriod ?? '',
    row.cutoffTime || '',
    row.forecastGeneration !== null && row.forecastGeneration !== undefined ? row.forecastGeneration : '',
    row.actualGeneration !== null && row.actualGeneration !== undefined ? row.actualGeneration : '',
    row.signedError !== null && row.signedError !== undefined ? row.signedError : '',
    row.absoluteError !== null && row.absoluteError !== undefined ? row.absoluteError : '',
    row.percentageError !== null && row.percentageError !== undefined ? row.percentageError : '',
    row.leadTimeHours !== null && row.leadTimeHours !== undefined ? row.leadTimeHours : '',
    row.status || '',
    row.forecastPublishTime || '',
    row.actualPublishTime || '',
  ]);

  const csvContent = [
    headers.join(','),
    ...rows.map((r) => r.map((field) => `"${String(field).replace(/"/g, '""')}"`).join(',')),
  ].join('\r\n');

  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');

  const dateSlug = metadata.date || 'data';
  const cutoffSlug = metadata.cutoff || 'cutoff';
  const resSlug = metadata.resolution || 'hourly';
  link.setAttribute('href', url);
  link.setAttribute('download', `windlens_${dateSlug}_${cutoffSlug}_${resSlug}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

