import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import type { Machine, SpecificationListItem } from '@/types/api';
import { CONTROL_CHART_ROWS } from '@tests/fixtures/controlChart';
import { jsonResponse, mockFetch, renderWithProviders } from '@tests/helpers';

import { ControlChartPanel } from './ControlChartPanel';

const specifications: SpecificationListItem[] = [
  {
    id: 2,
    product_id: 3,
    product_code: 'GEAR',
    characteristic: 'bore_diameter',
    target_value: '12.000',
    tolerance: '0.050',
    unit: 'mm',
  },
  {
    id: 5,
    product_id: 1,
    product_code: 'STEEL-SHAFT',
    characteristic: 'diameter',
    target_value: '20.000',
    tolerance: '0.100',
    unit: 'mm',
  },
];

const machines: Machine[] = [
  { id: 1, code: 'CNC-01', name: 'CNC Machine 01', status: 'IDLE', updated_at: '2026-11-02' },
  { id: 3, code: 'CNC-03', name: 'CNC Machine 03', status: 'WARNING', updated_at: '2026-11-02' },
];

const CHART_ROUTE = /\/analytics\/queries\/characteristic_control_chart/;
const WINDOW = { start: '2026-11-02T06:00', end: '2026-11-02T12:00' };

function chartResponse(url: string): Response {
  const params = new URL(url, 'http://localhost').searchParams;
  return jsonResponse({
    query: 'characteristic_control_chart',
    sql: 'WITH window_inspections AS (SELECT ... FROM inspections i)',
    params: { specification_id: Number(params.get('specification_id')) },
    rows: params.get('specification_id') === '5' ? CONTROL_CHART_ROWS : [],
  });
}

function chartCalls(fetchMock: ReturnType<typeof mockFetch>): URLSearchParams[] {
  return fetchMock.mock.calls
    .map(([input]) => String(input))
    .filter((url) => CHART_ROUTE.test(url))
    .map((url) => new URL(url, 'http://localhost').searchParams);
}

function setup(
  chartHandler: (url: string) => Response | Promise<Response> = chartResponse,
  machinesHandler: () => Response = () => jsonResponse(machines),
) {
  const fetchMock = mockFetch([
    [/\/specifications$/, () => jsonResponse(specifications)],
    [/\/machines$/, machinesHandler],
    [CHART_ROUTE, chartHandler],
  ]);
  renderWithProviders(<ControlChartPanel window={WINDOW} />);
  return fetchMock;
}

describe('ControlChartPanel', () => {
  it('defaults to the first specification and queries it with the page window', async () => {
    const fetchMock = setup();
    const select = await screen.findByLabelText('Specification');
    expect(
      within(select)
        .getAllByRole('option')
        .map((option) => option.textContent),
    ).toEqual(['GEAR bore_diameter (mm)', 'STEEL-SHAFT diameter (mm)']);
    expect(
      await screen.findByText('No inspections of this characteristic in the window'),
    ).toBeInTheDocument();
    const [params] = chartCalls(fetchMock);
    expect(params.get('specification_id')).toBe('2');
    expect(params.get('window_start')).toBe('2026-11-02T06:00:00');
    expect(params.get('window_end')).toBe('2026-11-02T12:00:00');
    expect(params.has('machine_id')).toBe(false);
  });

  it('shows a loading state while the chart query is in flight', async () => {
    let release: (() => void) | undefined;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    setup(async (url) => {
      await gate;
      return chartResponse(url);
    });
    expect(await screen.findByText('Loading control chart')).toBeInTheDocument();
    release?.();
    expect(
      await screen.findByText('No inspections of this characteristic in the window'),
    ).toBeInTheDocument();
  });

  it('plots the chosen specification, filters by machine, and explains the window', async () => {
    const fetchMock = setup();
    const user = userEvent.setup();
    await user.selectOptions(await screen.findByLabelText('Specification'), '5');
    expect(
      await screen.findByRole('heading', { name: 'X-bar chart: STEEL-SHAFT diameter (mm)' }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        /4 of 6 subgroups fall outside the control limits .* from batch SIM0001-CNC-03-02-B04 onward\./,
      ),
    ).toBeInTheDocument();
    expect(screen.getByText(/Each subgroup has its own limits/)).toBeVisible();
    expect(screen.getByRole('button', { name: 'Show the SQL' })).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText('Machine'), '3');
    await screen.findByRole('heading', { name: 'X-bar chart: STEEL-SHAFT diameter (mm)' });
    const last = chartCalls(fetchMock).at(-1);
    expect(last?.get('machine_id')).toBe('3');
    expect(last?.get('specification_id')).toBe('5');
  });

  it('keeps the chart and says so inline when the machine list cannot be loaded', async () => {
    setup(chartResponse, () =>
      jsonResponse(
        {
          error: 'DatabaseError',
          message: 'The database is unavailable',
          details: {},
          request_id: 'req-503',
        },
        503,
      ),
    );
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent(
      'The machine list could not be loaded, so the chart cannot be filtered by machine: The database is unavailable',
    );
    expect(within(alert).getByText('Request id req-503')).toBeInTheDocument();
    expect(
      await screen.findByText('No inspections of this characteristic in the window'),
    ).toBeInTheDocument();
    expect(
      within(screen.getByLabelText('Machine'))
        .getAllByRole('option')
        .map((option) => option.textContent),
    ).toEqual(['All machines']);
  });

  it('shows the API message when the query is rejected instead of crashing', async () => {
    setup(() =>
      jsonResponse(
        {
          error: 'ValidationError',
          message: 'specification_id is required for this query',
          details: {},
          request_id: 'req-422',
        },
        422,
      ),
    );
    const alert = await screen.findByRole('alert');
    expect(
      within(alert).getByText('specification_id is required for this query'),
    ).toBeInTheDocument();
    expect(within(alert).getByText('Request id req-422')).toBeInTheDocument();
    expect(screen.getByLabelText('Specification')).toBeInTheDocument();
  });
});
