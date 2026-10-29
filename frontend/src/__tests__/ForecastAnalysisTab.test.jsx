import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import ForecastAnalysisTab from '../components/ForecastAnalysisTab';

describe('ForecastAnalysisTab Component', () => {
  const mockIntervals = [
    {
      startTime: '2026-01-01T00:00:00Z',
      actualGeneration: 14000.0,
      forecastGeneration: 14500.0,
      signedError: 500.0,
      status: 'matched',
    },
    {
      startTime: '2026-01-01T01:00:00Z',
      actualGeneration: 13000.0,
      forecastGeneration: 12500.0,
      signedError: -500.0,
      status: 'matched',
    },
  ];

  it('renders correlation stats and chart titles', () => {
    render(<ForecastAnalysisTab intervals={mockIntervals} resolution="hourly" />);

    expect(screen.getByText(/Pearson Correlation/i)).toBeInTheDocument();
    expect(screen.getByText(/Coefficient of Det/i)).toBeInTheDocument();
    expect(screen.getByText(/Actual vs Forecast Correlation/i)).toBeInTheDocument();
    expect(screen.getByText(/Forecast Error Distribution/i)).toBeInTheDocument();
  });

  it('displays empty message when no matched intervals exist', () => {
    render(<ForecastAnalysisTab intervals={[]} resolution="hourly" />);
    expect(screen.getByText(/No matched forecast\/actual generation data/i)).toBeInTheDocument();
  });
});

