import { render, screen } from '@testing-library/react';
import { cloneElement } from 'react';
import type { ReactElement } from 'react';
import type * as Recharts from 'recharts';
import { describe, expect, it, vi } from 'vitest';

import { toControlChartSeries } from '@/utils/chartTransforms';
import { CONTROL_CHART_ROWS, controlChartRows, subgroupRow } from '@tests/fixtures/controlChart';

import { ControlChart } from './ControlChart';

/** jsdom reports a zero-size container, so the chart is given a fixed size to render into. */
vi.mock('recharts', async (importOriginal) => {
  const actual = await importOriginal<typeof Recharts>();
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: ReactElement<Record<string, unknown>> }) => (
      <div style={{ width: 800, height: 340 }}>
        {cloneElement(children, { width: 800, height: 340 })}
      </div>
    ),
  };
});

function layers(container: HTMLElement, className: string): number {
  return container.querySelectorAll(`.${className}`).length;
}

describe('ControlChart', () => {
  it('draws the grand mean, stepped control limits, both specification limits, and marks the points outside', () => {
    const { container } = render(
      <ControlChart series={toControlChartSeries(CONTROL_CHART_ROWS)} unit="mm" />,
    );
    expect(screen.getByRole('img', { name: /control chart/i })).toBeInTheDocument();
    expect(layers(container, 'control-chart-grand-mean')).toBe(1);
    expect(layers(container, 'control-chart-spec-limit')).toBe(2);
    const limitPaths = container.querySelectorAll(
      '.control-chart-control-limit path.recharts-line-curve',
    );
    expect(limitPaths).toHaveLength(2);
    expect(container.querySelectorAll('[data-out-of-control="true"]')).toHaveLength(4);
    expect(container.querySelectorAll('[data-out-of-control="false"]')).toHaveLength(2);
    expect(screen.getByText('Control limits (UCL, LCL), per subgroup')).toBeInTheDocument();
    expect(screen.getByText('Specification limits')).toBeInTheDocument();
    expect(screen.getByText('View data table')).toBeInTheDocument();
  });

  it('steps the limits per subgroup so a small subgroup with the same mean is inside its wider limits', () => {
    const rows = [
      subgroupRow(1, 'B01', 20.0758),
      subgroupRow(2, 'B02', 20.0758, { sample_count: 5 }),
      subgroupRow(3, 'B03', 20.0758),
    ];
    const { container } = render(<ControlChart series={toControlChartSeries(rows)} unit="mm" />);
    const marks = Array.from(container.querySelectorAll('[data-out-of-control]')).map((dot) =>
      dot.getAttribute('data-out-of-control'),
    );
    expect(marks).toEqual(['true', 'false', 'true']);
    const [uclPath] = container.querySelectorAll(
      '.control-chart-control-limit path.recharts-line-curve',
    );
    expect(uclPath.getAttribute('d')).toMatch(/^M[^L]*L/);
  });

  it('shows the empty state when there are no subgroups', () => {
    const { container } = render(<ControlChart series={toControlChartSeries([])} unit="mm" />);
    expect(
      screen.getByText('No inspections of this characteristic in the window'),
    ).toBeInTheDocument();
    expect(container.querySelector('svg')).toBeNull();
  });

  it('omits the control limit lines and markers when ucl and lcl are null', () => {
    const series = toControlChartSeries(controlChartRows({ ucl: null, lcl: null }));
    const { container } = render(<ControlChart series={series} unit="mm" />);
    expect(layers(container, 'control-chart-grand-mean')).toBe(1);
    expect(layers(container, 'control-chart-control-limit')).toBe(0);
    expect(layers(container, 'control-chart-spec-limit')).toBe(2);
    expect(container.querySelectorAll('[data-out-of-control="true"]')).toHaveLength(0);
    expect(container.querySelectorAll('[data-out-of-control="false"]')).toHaveLength(6);
    expect(screen.queryByText(/Control limits \(UCL, LCL\)/)).not.toBeInTheDocument();
  });
});
