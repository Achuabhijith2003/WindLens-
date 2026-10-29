/**
 * Centralized API Service for communicating with WindLens FastAPI backend.
 */

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? (import.meta.env.DEV ? 'http://localhost:8000' : '')).replace(/\/$/, '');

function buildUrl(endpoint) {
  const cleanEndpoint = endpoint.replace(/^\//, '');
  if (API_BASE_URL.startsWith('http://') || API_BASE_URL.startsWith('https://')) {
    return new URL(`${API_BASE_URL}/${cleanEndpoint}`);
  }
  const origin = typeof window !== 'undefined' && window.location?.origin ? window.location.origin : 'http://localhost:8000';
  const cleanBase = API_BASE_URL.replace(/^\//, '');
  const fullPath = cleanBase ? `${cleanBase}/${cleanEndpoint}` : cleanEndpoint;
  return new URL(fullPath, origin);
}

async function fetchJson(endpoint, params = {}) {
  const url = buildUrl(endpoint);
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      url.searchParams.append(key, value);
    }
  });

  let response;
  try {
    response = await fetch(url.toString(), {
      headers: {
        Accept: 'application/json',
      },
    });
  } catch (err) {
    throw new Error(`Network error connecting to WindLens backend at ${API_BASE_URL}: ${err.message}`);
  }

  if (!response.ok) {
    let errorDetail = `HTTP ${response.status} ${response.statusText}`;
    try {
      const errBody = await response.json();
      if (errBody && errBody.detail) {
        errorDetail = errBody.detail;
      }
    } catch {
      // Non-JSON error body
    }
    throw new Error(errorDetail);
  }

  return response.json();
}

export const apiService = {
  async checkHealth() {
    return fetchJson('api/health');
  },

  async getOverview(date = '2026-01-01', cutoff = 'day_ahead_1700', resolution = 'hourly') {
    return fetchJson('api/overview', { date, cutoff, resolution });
  },

  async getTimeseries(date = '2026-01-01', cutoff = 'day_ahead_1700', resolution = 'hourly') {
    return fetchJson('api/timeseries', { date, cutoff, resolution });
  },

  async getAccuracy(fromDate = '2026-01-01', toDate = '2026-01-31', cutoff = 'day_ahead_1700', resolution = 'hourly') {
    return fetchJson('api/accuracy', { from: fromDate, to: toDate, cutoff, resolution });
  },
};

