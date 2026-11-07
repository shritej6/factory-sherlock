import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import type { Alert, OrderStatusCounts, OverdueCheckResponse, UserRole } from '@/types/api';
import {
  jsonResponse,
  makeUser,
  mockFetch,
  pageResponse,
  renderWithProviders,
} from '@tests/helpers';

import { OverviewPage } from './OverviewPage';

const alert: Alert = {
  id: 3,
  machine_id: 1,
  production_order_id: null,
  alert_type: 'HIGH_DEFECT_RATE',
  severity: 'CRITICAL',
  message: 'Defect rate on CNC-01 exceeded 15%',
  created_at: '2026-11-03T09:00:00',
  acknowledged_at: null,
};

const overdueAlert: Alert = {
  id: 4,
  machine_id: null,
  production_order_id: 7,
  alert_type: 'ORDER_OVERDUE',
  severity: 'WARNING',
  message: 'Order ORD-7 is 2 days overdue (due 2026-11-01)',
  created_at: '2026-11-03T09:05:00',
  acknowledged_at: null,
};

const CHECK_URL = /\/analytics\/alerts\/checks\/overdue-orders$/;
const STATUS_COUNTS_URL = /\/production-orders\/status-counts$/;
const OPEN_INVESTIGATIONS_URL = /\/investigations\?status=OPEN&status=IN_REVIEW&limit=1&offset=0$/;

const statusCounts: OrderStatusCounts = {
  PLANNED: 2,
  RELEASED: 4,
  IN_PROGRESS: 3,
  COMPLETED: 9,
  CANCELLED: 1,
};

function checkResponse(raised: number): OverdueCheckResponse {
  return { checked: 9, raised, alerts: raised > 0 ? [overdueAlert] : [] };
}

function setup(
  role: UserRole = 'ENGINEER',
  check: () => Response = () => jsonResponse(null),
  alerts: Alert[] = [alert],
) {
  const fetchMock = mockFetch([
    [CHECK_URL, check],
    [/\/analytics\/alerts/, () => pageResponse(alerts, 37, 10)],
    [STATUS_COUNTS_URL, () => jsonResponse(statusCounts)],
    [OPEN_INVESTIGATIONS_URL, () => pageResponse([], 3, 1)],
    [/\/investigations/, () => pageResponse([], 0)],
    [/\/quality\/summary/, () => jsonResponse(null)],
  ]);
  renderWithProviders(<OverviewPage />, { user: makeUser(role) });
  return fetchMock;
}

const checkButton = () => screen.getByRole('button', { name: 'Check overdue orders' });

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

  it('counts active orders from one status-counts request instead of a list per status', async () => {
    const fetchMock = setup();
    expect(await screen.findByText('7')).toBeInTheDocument();
    expect(screen.getByText('released or in progress')).toBeInTheDocument();
    const orderCalls = fetchMock.mock.calls
      .map(([input]) => String(input))
      .filter((url) => url.includes('/production-orders'));
    expect(orderCalls).toHaveLength(1);
    expect(orderCalls[0]).toMatch(STATUS_COUNTS_URL);
  });

  it('counts open and in-review investigations from the total of a filtered one-row page', async () => {
    const fetchMock = setup();
    expect(await screen.findByText('3')).toBeInTheDocument();
    expect(screen.getByText('open or in review')).toBeInTheDocument();
    const countCall = fetchMock.mock.calls
      .map(([input]) => String(input))
      .find((url) => OPEN_INVESTIGATIONS_URL.test(url));
    const params = new URL(String(countCall), 'http://localhost').searchParams;
    expect(params.getAll('status')).toEqual(['OPEN', 'IN_REVIEW']);
    expect(params.get('limit')).toBe('1');
    const listCalls = fetchMock.mock.calls
      .map(([input]) => String(input))
      .filter((url) => url.includes('/investigations') && !OPEN_INVESTIGATIONS_URL.test(url));
    expect(listCalls).toHaveLength(1);
    expect(new URL(listCalls[0], 'http://localhost').searchParams.get('limit')).toBe('5');
  });

  it('links alerts that belong to a production order to the orders screen', async () => {
    setup('VIEWER', undefined, [alert, overdueAlert]);
    const link = await screen.findByRole('link', { name: 'Open orders for alert 4' });
    expect(link).toHaveAttribute('href', '/orders');
    expect(screen.queryByRole('link', { name: 'Open orders for alert 3' })).not.toBeInTheDocument();
  });

  describe('overdue order check', () => {
    it('hides the button from viewers', async () => {
      setup('VIEWER');
      await screen.findByText('Defect rate on CNC-01 exceeded 15%');
      expect(
        screen.queryByRole('button', { name: 'Check overdue orders' }),
      ).not.toBeInTheDocument();
    });

    it.each<UserRole>(['OPERATOR', 'ENGINEER', 'ADMIN'])('shows the button to %s', async (role) => {
      setup(role);
      await screen.findByText('Defect rate on CNC-01 exceeded 15%');
      expect(checkButton()).toBeEnabled();
    });

    it('posts without a body, reports the raised alerts, and reloads the list', async () => {
      const fetchMock = setup('OPERATOR', () => jsonResponse(checkResponse(2)));
      const user = userEvent.setup();
      await screen.findByText('Defect rate on CNC-01 exceeded 15%');
      const listCallsBefore = fetchMock.mock.calls.filter(([input]) =>
        /\/analytics\/alerts\?/.test(String(input)),
      ).length;

      await user.click(checkButton());

      expect(
        await screen.findByText('Checked 9 open orders, raised 2 overdue alerts'),
      ).toBeInTheDocument();
      const checkCall = fetchMock.mock.calls.find(([input]) => CHECK_URL.test(String(input)));
      expect(checkCall?.[1]).toMatchObject({ method: 'POST' });
      expect(checkCall?.[1]).toHaveProperty('body', undefined);
      await waitFor(() => {
        const listCallsAfter = fetchMock.mock.calls.filter(([input]) =>
          /\/analytics\/alerts\?/.test(String(input)),
        ).length;
        expect(listCallsAfter).toBe(listCallsBefore + 1);
      });
    });

    it('says when no new alerts were raised', async () => {
      setup('ENGINEER', () => jsonResponse(checkResponse(0)));
      const user = userEvent.setup();
      await screen.findByText('Defect rate on CNC-01 exceeded 15%');
      await user.click(checkButton());
      expect(
        await screen.findByText('Checked 9 open orders, no new overdue alerts'),
      ).toBeInTheDocument();
    });

    it('shows the server message when the check fails', async () => {
      setup('ENGINEER', () =>
        jsonResponse(
          { error: 'ConflictError', message: 'Overdue check already running', details: {} },
          409,
        ),
      );
      const user = userEvent.setup();
      await screen.findByText('Defect rate on CNC-01 exceeded 15%');
      await user.click(checkButton());
      const notice = await screen.findByRole('alert');
      expect(notice).toHaveTextContent('Overdue check already running');
    });
  });
});
