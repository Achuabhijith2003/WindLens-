import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import FilterPanel from '../components/FilterPanel';

describe('FilterPanel Component', () => {
  it('renders default controls correctly', () => {
    render(
      <FilterPanel
        deliveryDate="2026-01-01"
        onDateChange={vi.fn()}
        cutoff="day_ahead_1700"
        onCutoffChange={vi.fn()}
        resolution="hourly"
        onResolutionChange={vi.fn()}
        rangeMode={false}
        onRangeModeToggle={vi.fn()}
        fromDate="2026-01-01"
        onFromDateChange={vi.fn()}
        toDate="2026-01-03"
        onToDateChange={vi.fn()}
        onRefresh={vi.fn()}
        loading={false}
      />
    );

    expect(screen.getByDisplayValue('2026-01-01')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /refresh/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /multi-day range/i })).toBeInTheDocument();
  });

  it('triggers onDateChange when date input changes', () => {
    const onDateChange = vi.fn();
    render(
      <FilterPanel
        deliveryDate="2026-01-01"
        onDateChange={onDateChange}
        cutoff="day_ahead_1700"
        onCutoffChange={vi.fn()}
        resolution="hourly"
        onResolutionChange={vi.fn()}
        rangeMode={false}
        onRangeModeToggle={vi.fn()}
        fromDate="2026-01-01"
        onFromDateChange={vi.fn()}
        toDate="2026-01-03"
        onToDateChange={vi.fn()}
        onRefresh={vi.fn()}
        loading={false}
      />
    );

    const dateInput = screen.getByDisplayValue('2026-01-01');
    fireEvent.change(dateInput, { target: { value: '2026-01-02' } });
    expect(onDateChange).toHaveBeenCalledWith('2026-01-02');
  });

  it('triggers onResolutionChange when resolution buttons are clicked', () => {
    const onResolutionChange = vi.fn();
    render(
      <FilterPanel
        deliveryDate="2026-01-01"
        onDateChange={vi.fn()}
        cutoff="day_ahead_1700"
        onCutoffChange={vi.fn()}
        resolution="hourly"
        onResolutionChange={onResolutionChange}
        rangeMode={false}
        onRangeModeToggle={vi.fn()}
        fromDate="2026-01-01"
        onFromDateChange={vi.fn()}
        toDate="2026-01-03"
        onToDateChange={vi.fn()}
        onRefresh={vi.fn()}
        loading={false}
      />
    );

    const halfHourlyBtn = screen.getByRole('button', { name: /half-hourly/i });
    fireEvent.click(halfHourlyBtn);
    expect(onResolutionChange).toHaveBeenCalledWith('half_hourly');
  });
});

