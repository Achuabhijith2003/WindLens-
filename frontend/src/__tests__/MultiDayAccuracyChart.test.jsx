import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import MultiDayAccuracyChart from '../components/MultiDayAccuracyChart';

describe('MultiDayAccuracyChart Component', () => {
  const mockDailyBreakdown = [
    {
      date: '2026-01-01',
      matchedCount: 24,
      expectedCount: 24,
      metrics: {
        mae_mw: 4217.4,
        rmse_mw: 4277.9,
        signed_bias_mw: 4217.4,
        mape_pct: 27.65,
        data_completeness_pct: 100.0,
      },
    },
    {
      date: '2026-01-02',
      matchedCount: 24,
      expectedCount: 24,
      metrics: {
        mae_mw: 1500.0,
        rmse_mw: 1800.0,
        signed_bias_mw: -500.0,
        mape_pct: 12.5,
        data_completeness_pct: 100.0,
      },
    },
  ];

  it('renders multi-day accuracy chart header and highlights', () => {
    render(
      <MultiDayAccuracyChart
        dailyBreakdown={mockDailyBreakdown}
        fromDate="2026-01-01"
        toDate="2026-01-02"
        cutoff="day_ahead_1700"
        resolution="hourly"
      />
    );

    expect(screen.getByText(/Multi-Day Accuracy & Bias Evolution/i)).toBeInTheDocument();
    expect(screen.getByText(/Most Accurate Day/i)).toBeInTheDocument();
    expect(screen.getByText(/Highest Error Day/i)).toBeInTheDocument();
    expect(screen.getByText(/Mean Daily MAE/i)).toBeInTheDocument();
    expect(screen.getByText(/1,500.0 MW/i)).toBeInTheDocument();
  });

  it('allows toggling between chart modes', () => {
    render(
      <MultiDayAccuracyChart
        dailyBreakdown={mockDailyBreakdown}
        fromDate="2026-01-01"
        toDate="2026-01-02"
        cutoff="day_ahead_1700"
        resolution="hourly"
      />
    );

    const biasButton = screen.getByRole('button', { name: /Signed Bias \(MW\)/i });
    fireEvent.click(biasButton);
    expect(biasButton).toHaveClass('btn-active');

    const mapeButton = screen.getByRole('button', { name: /MAPE \(%\)/i });
    fireEvent.click(mapeButton);
    expect(mapeButton).toHaveClass('btn-active');
  });

  it('renders nothing when daily breakdown is empty', () => {
    const { container } = render(<MultiDayAccuracyChart dailyBreakdown={[]} />);
    expect(container.firstChild).toBeNull();
  });
});

