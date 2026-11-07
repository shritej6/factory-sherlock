import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import type { Alert } from '@/types/api';
import { jsonResponse, makeUser, mockFetch, renderWithProviders } from '@tests/helpers';

import { AlertsList } from './AlertsList';

const alerts: Alert[] = [
  {
    id: 3,
    machine_id: 1,
    production_order_id: null,
    alert_type: 'HIGH_DEFECT_RATE',
    severity: 'CRITICAL',
    message: 'Defect rate on CNC-01 exceeded 15%',
    created_at: '2026-11-03T09:00:00',
    acknowledged_at: null,
  },
  {
    id: 4,
    machine_id: null,
    production_order_id: 7,
    alert_type: 'ORDER_OVERDUE',
    severity: 'WARNING',
    message: 'Order ORD-7 is 2 days overdue (due 2026-11-01)',
    created_at: '2026-11-03T09:05:00',
    acknowledged_at: null,
  },
];

const ACKNOWLEDGE_ROUTE = /\/analytics\/alerts\/(\d+)\/acknowledge$/;

describe('AlertsList', () => {
  it('names each acknowledge button after its alert while keeping the visible text', () => {
    mockFetch([]);
    renderWithProviders(<AlertsList alerts={alerts} />, { user: makeUser('OPERATOR') });
    const button = screen.getByRole('button', { name: 'Acknowledge alert 3' });
    expect(button).toHaveTextContent('Acknowledge');
    expect(screen.getByRole('button', { name: 'Acknowledge alert 4' })).toBeInTheDocument();
  });

  it('shows the backend message and request id when acknowledging fails', async () => {
    const fetchMock = mockFetch([
      [
        ACKNOWLEDGE_ROUTE,
        () =>
          jsonResponse(
            {
              error: 'ConflictError',
              message: 'Alert 4 is already acknowledged',
              details: {},
              request_id: 'req-409',
            },
            409,
          ),
      ],
    ]);
    renderWithProviders(<AlertsList alerts={alerts} />, { user: makeUser('ENGINEER') });
    await userEvent.click(screen.getByRole('button', { name: 'Acknowledge alert 4' }));

    const alert = await screen.findByRole('alert');
    expect(within(alert).getByText('Alert 4 is already acknowledged')).toBeInTheDocument();
    expect(within(alert).getByText('Request id req-409')).toBeInTheDocument();
    const call = fetchMock.mock.calls.find(([url]) => ACKNOWLEDGE_ROUTE.test(String(url)));
    expect(String(call?.[0])).toMatch(/\/analytics\/alerts\/4\/acknowledge$/);
    expect(call?.[1]).toMatchObject({ method: 'POST' });
  });

  it('offers no acknowledge control to a viewer', () => {
    mockFetch([]);
    renderWithProviders(<AlertsList alerts={alerts} />, { user: makeUser('VIEWER') });
    expect(screen.queryByRole('button', { name: /acknowledge alert/i })).not.toBeInTheDocument();
  });
});
