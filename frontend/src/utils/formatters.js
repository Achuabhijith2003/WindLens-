/**
 * Formatting utilities for timestamps, generation MW, percentages, and errors.
 */

export function formatMW(val, decimals = 1) {
  if (val === null || val === undefined || isNaN(val)) return '—';
  return `${Number(val).toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals })} MW`;
}

export function formatNumber(val, decimals = 1) {
  if (val === null || val === undefined || isNaN(val)) return '—';
  return Number(val).toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

export function formatPercent(val, decimals = 1) {
  if (val === null || val === undefined || isNaN(val)) return '—';
  return `${Number(val).toFixed(decimals)}%`;
}

export function formatIsoTime(isoString) {
  if (!isoString) return '—';
  try {
    const dt = new Date(isoString);
    return dt.toLocaleTimeString('en-GB', {
      hour: '2-digit',
      minute: '2-digit',
      timeZone: 'UTC',
    }) + ' UTC';
  } catch {
    return isoString;
  }
}

export function formatIsoDateTime(isoString) {
  if (!isoString) return '—';
  try {
    const dt = new Date(isoString);
    const datePart = dt.toISOString().slice(0, 10);
    const timePart = dt.toLocaleTimeString('en-GB', {
      hour: '2-digit',
      minute: '2-digit',
      timeZone: 'UTC',
    });
    return `${datePart} ${timePart} UTC`;
  } catch {
    return isoString;
  }
}

