import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import IntervalTable from '../components/IntervalTable';

describe('IntervalTable Component', () => {
  const mockIntervals = [
    {
      startTime: '2026-01-01T00:00:00Z',
      settlementDate: '2026-01-01',
      settlementPeriod: 1,
      cutoffTime: '2025-12-31T17:00:00Z',
      actualGeneration: 14000.0,
      actualPublishTime: '2026-01-01T00:45:00Z',
      forecastGeneration: 14500.0,
      forecastPublishTime: '2025-12-31T15:00:00Z',
      leadTimeHours: 9.0,
      signedError: 500.0,
      absoluteError: 500.0,
      percentageError: 3.57,
      status: 'matched',
    },
    {
      startTime: '2026-01-01T00:30:00Z',
      settlementDate: '2026-01-01',
      settlementPeriod: 2,
      cutoffTime: '2025-12-31T17:00:00Z',
      actualGeneration: 14200.0,
      actualPublishTime: '2026-01-01T01:15:00Z',
      forecastGeneration: null,
      forecastPublishTime: null,
      leadTimeHours: null,
      signedError: null,
      absoluteError: null,
      percentageError: null,
      status: 'resolution_mismatch',
    },
  ];

  it('renders table rows and status badges correctly', () => {
    render(<IntervalTable intervals={mockIntervals} resolution="half_hourly" />);

    expect(screen.getByText('14,500.0')).toBeInTheDocument();
    expect(screen.getByText('14,000.0')).toBeInTheDocument();
    expect(screen.getByText('+500.0')).toBeInTheDocument();
    expect(screen.getByText('matched')).toBeInTheDocument();
    expect(screen.getByText('mismatch (:30)')).toBeInTheDocument();
  });

  it('filters rows when status dropdown changes', () => {
    render(<IntervalTable intervals={mockIntervals} resolution="half_hourly" />);

    const select = screen.getByRole('combobox');
    fireEvent.change(select, { target: { value: 'matched' } });

    expect(screen.getByText('14,500.0')).toBeInTheDocument();
    expect(screen.queryByText('mismatch (:30)')).not.toBeInTheDocument();
  });

  it('filters rows by search query', () => {
    render(<IntervalTable intervals={mockIntervals} resolution="half_hourly" />);

    const searchInput = screen.getByPlaceholderText(/search time/i);
    fireEvent.change(searchInput, { target: { value: '00:30' } });

    expect(screen.queryByText('14,500.0')).not.toBeInTheDocument();
    expect(screen.getByText('14,200.0')).toBeInTheDocument();
  });
});

