import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import ErrorAnalysisTab from '../components/ErrorAnalysisTab';

describe('ErrorAnalysisTab Component', () => {
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

  it('renders signed error timeline, diurnal bias, and extreme deviations', () => {
    render(<ErrorAnalysisTab intervals={mockIntervals} resolution="hourly" />);

    expect(screen.getByText(/Signed Forecast Error Over Time/i)).toBeInTheDocument();
    expect(screen.getByText(/Diurnal Bias Profile/i)).toBeInTheDocument();
    expect(screen.getByText(/Extreme Forecast Deviations/i)).toBeInTheDocument();
    expect(screen.getByText(/\+500\.0 MW/i)).toBeInTheDocument();
    expect(screen.getByText(/-500\.0 MW/i)).toBeInTheDocument();
  });

  it('displays empty message when no matched data is provided', () => {
    render(<ErrorAnalysisTab intervals={[]} resolution="hourly" />);
    expect(screen.getByText(/No matched error data available/i)).toBeInTheDocument();
  });
});
