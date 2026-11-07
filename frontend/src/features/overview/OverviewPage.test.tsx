import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import type { Alert } from '@/types/api';
import { jsonResponse, mockFetch, pageResponse, renderWithProviders } from '@tests/helpers';

import { OverviewPage } from './OverviewPage';

const alert: Alert = {
  id: 3,
  machine_id: 1,
  alert_type: 'HIGH_DEFECT_RATE',
  severity: 'CRITICAL',
  message: 'Defect rate on CNC-01 exceeded 15%',
  created_at: '2026-11-03T09:00:00',
  acknowledged_at: null,
};

function setup() {
  const fetchMock = mockFetch([
    [/\/analytics\/alerts/, () => pageResponse([alert], 37, 10)],
    [/\/production-orders\?.*status=RELEASED/, () => pageResponse([], 4, 1)],
    [/\/production-orders\?.*status=IN_PROGRESS/, () => pageResponse([], 3, 1)],
    [/\/investigations/, () => pageResponse([], 0)],
    [/\/quality\/summary/, () => jsonResponse(null)],
  ]);
  renderWithProviders(<OverviewPage />);
  return fetchMock;
}

describe('OverviewPage', () => {
  it('pages alerts ten at a time and reports the total', async () => {
    const fetchMock = setup();
    expect(await screen.findByText('Defect rate on CNC-01 exceeded 15%')).toBeInTheDocument();
    expect(screen.getByText('Showing 1 to 10 of 37')).toBeInTheDocument();
    const alertsCall = fetchMock.mock.calls.find(([input]) =>
      String(input).includes('/analytics/alerts'),
    );
    const params = new URL(String(alertsCall?.[0]), 'http://localhost').searchParams;
    expect(params.get('limit')).toBe('10');
    expect(params.get('offset')).toBe('0');
    const sizes = Array.from(screen.getByLabelText('Rows per page').querySelectorAll('option'));
    expect(sizes.map((o) => o.value)).toEqual(['10', '25', '50']);
  });

  it('requests the next ten alerts when next is clicked', async () => {
    const fetchMock = setup();
    const user = userEvent.setup();
    await screen.findByText('Showing 1 to 10 of 37');
    await user.click(screen.getByRole('button', { name: 'Next page' }));
    await screen.findByText('Showing 11 to 20 of 37');
    const last = fetchMock.mock.calls
      .map(([input]) => String(input))
      .filter((url) => url.includes('/analytics/alerts'))
      .at(-1);
    expect(new URL(String(last), 'http://localhost').searchParams.get('offset')).toBe('10');
  });

  it('counts active orders from the envelope totals instead of the rows on one page', async () => {
    setup();
    expect(await screen.findByText('7')).toBeInTheDocument();
    expect(screen.getByText('released or in progress')).toBeInTheDocument();
  });
});
