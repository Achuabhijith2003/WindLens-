import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import KpiCards from '../components/KpiCards';

describe('KpiCards Component', () => {
  it('renders loading state when metrics is null', () => {
    render(<KpiCards metrics={null} />);
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it('renders calculated KPI metrics correctly', () => {
    const mockMetrics = {
      mae_mw: 4217.4,
      rmse_mw: 4277.9,
      signed_bias_mw: 4217.4,
      mape_pct: 27.65,
      mape_excluded_zero_count: 0,
      matched_intervals_count: 24,
      expected_interval_count: 24,
      data_completeness_pct: 100.0,
      selected_cutoff: 'day_ahead_1700',
    };

    render(<KpiCards metrics={mockMetrics} resolution="hourly" />);

    expect(screen.getByText('4,217.4')).toBeInTheDocument();
    expect(screen.getByText('4,277.9')).toBeInTheDocument();
    expect(screen.getByText('+4,217.4')).toBeInTheDocument();
    expect(screen.getByText('27.65%')).toBeInTheDocument();
    expect(screen.getByText('100.0%')).toBeInTheDocument();
    expect(screen.getByText('Over-forecasting')).toBeInTheDocument();
  });

  it('displays excluded zero actuals message when zeros exist', () => {
    const mockMetrics = {
      mae_mw: 100.0,
      rmse_mw: 120.0,
      signed_bias_mw: -50.0,
      mape_pct: 15.0,
      mape_excluded_zero_count: 3,
      matched_intervals_count: 20,
      expected_interval_count: 24,
      data_completeness_pct: 83.33,
    };

    render(<KpiCards metrics={mockMetrics} resolution="hourly" />);
    expect(screen.getByText(/3 zeros excluded/i)).toBeInTheDocument();
    expect(screen.getByText('Under-forecasting')).toBeInTheDocument();
  });
});

