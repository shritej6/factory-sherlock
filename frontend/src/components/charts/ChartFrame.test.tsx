import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { ChartFrame } from './ChartFrame';

describe('ChartFrame', () => {
  it('offers the plotted rows as a data table beneath the chart', () => {
    render(
      <ChartFrame
        title="Defect rate by machine"
        description="Failed over inspected."
        empty={false}
        tableRows={[{ machine: 'CNC-03', defect_rate: 0.0958, failed: 46 }]}
      >
        <svg aria-hidden="true" />
      </ChartFrame>,
    );
    expect(screen.getByRole('img', { name: /defect rate by machine/i })).toBeInTheDocument();
    const details = screen.getByText('View data table').closest('details');
    expect(details).not.toBeNull();
    const table = within(details as HTMLElement).getByRole('table', {
      name: 'Defect rate by machine data',
    });
    expect(within(table).getByText('CNC-03')).toBeInTheDocument();
    expect(within(table).getByText('9.6%')).toBeInTheDocument();
  });

  it('shows the empty state and no table when there is nothing to plot', () => {
    render(
      <ChartFrame title="Daily production trend" empty tableRows={[]}>
        <svg aria-hidden="true" />
      </ChartFrame>,
    );
    expect(screen.getByText('No data for this window')).toBeInTheDocument();
    expect(screen.queryByText('View data table')).not.toBeInTheDocument();
  });
});
