import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import type { QueryCatalogEntry } from '@/types/api';
import { jsonResponse, mockFetch, renderWithProviders } from '@tests/helpers';

import { SqlExplorer } from './SqlExplorer';

const catalog: QueryCatalogEntry[] = [
  {
    name: 'daily_production_trend',
    description: 'Query 09: Daily production trend',
    sql: 'SELECT production_date FROM ...',
    runnable: true,
    parameters: ['window_start', 'window_end'],
  },
  {
    name: 'order_completion_summary',
    description: 'Query 07: Order completion',
    sql: 'SELECT status FROM ...',
    runnable: true,
    parameters: [],
  },
  {
    name: 'unit_backward_trace',
    description: 'Query 05: Unit backward traceability',
    sql: 'SELECT u.serial_number FROM production_units u',
    runnable: false,
    parameters: [],
  },
  {
    name: 'investigation.defect_onset',
    description: 'Investigation query: hourly defect rate',
    sql: 'SELECT bucket_start FROM ...',
    runnable: false,
    parameters: [],
  },
];

function setup() {
  const fetchMock = mockFetch([
    [/\/analytics\/queries$/, () => jsonResponse(catalog)],
    [
      /\/analytics\/queries\/order_completion_summary/,
      () =>
        jsonResponse({
          query: 'order_completion_summary',
          sql: 'SELECT status FROM ...',
          params: {},
          rows: [{ status: 'COMPLETED', orders: 2 }],
        }),
    ],
  ]);
  renderWithProviders(
    <SqlExplorer defaultWindow={{ start: '2026-11-01T00:00', end: '2026-11-05T00:00' }} />,
  );
  return fetchMock;
}

describe('SqlExplorer', () => {
  it('lists every catalog entry and marks the read-only ones', async () => {
    setup();
    const select = await screen.findByLabelText('Query');
    const labels = within(select)
      .getAllByRole('option')
      .map((o) => o.textContent);
    expect(labels).toEqual([
      'daily_production_trend',
      'order_completion_summary',
      'unit_backward_trace (read only)',
      'investigation.defect_onset (read only)',
    ]);
  });

  it('shows only the controls a runnable query binds and sends those parameters', async () => {
    const fetchMock = setup();
    const user = userEvent.setup();
    const select = await screen.findByLabelText('Query');
    expect(screen.getByLabelText('Window start')).toBeInTheDocument();
    await user.selectOptions(select, 'order_completion_summary');
    expect(screen.queryByLabelText('Window start')).not.toBeInTheDocument();
    expect(screen.getByText('This query takes no parameters.')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Run query' }));
    expect(await screen.findByText('COMPLETED')).toBeInTheDocument();
    const runCall = fetchMock.mock.calls.find(([url]) =>
      String(url).includes('/analytics/queries/order_completion_summary'),
    );
    expect(String(runCall?.[0])).toBe('/api/v1/analytics/queries/order_completion_summary');
  });

  it('lets a read-only query be opened for its SQL with an explanatory note and no run button', async () => {
    setup();
    const user = userEvent.setup();
    await user.selectOptions(await screen.findByLabelText('Query'), 'unit_backward_trace');
    expect(screen.getByText(/runs from the Material Traceability screen/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Run query' })).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Show the SQL' }));
    expect(screen.getByText(/FROM production_units u/)).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText('Query'), 'investigation.defect_onset');
    expect(screen.getByText(/run by the investigation engine/)).toBeInTheDocument();
  });
});
