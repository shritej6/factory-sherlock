import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import type { ProductionOrder } from '@/types/api';
import { makeUser, mockFetch, pageResponse, renderWithProviders } from '@tests/helpers';

import { OrdersPage } from './OrdersPage';

const order: ProductionOrder = {
  id: 7,
  order_number: 'ORD-7',
  product_id: 1,
  machine_id: 1,
  quantity_planned: 80,
  quantity_completed: 20,
  status: 'IN_PROGRESS',
  due_date: '2026-11-05',
  created_at: '2026-11-02T10:00:00',
  updated_at: '2026-11-02T10:00:00',
};

function setup(role: 'VIEWER' | 'OPERATOR' | 'ENGINEER', total = 1) {
  const fetchMock = mockFetch([[/\/production-orders/, () => pageResponse([order], total)]]);
  renderWithProviders(<OrdersPage />, { user: makeUser(role) });
  return fetchMock;
}

function orderRequests(fetchMock: ReturnType<typeof mockFetch>): URLSearchParams[] {
  return fetchMock.mock.calls
    .map(([input]) => String(input))
    .filter((url) => url.includes('/production-orders'))
    .map((url) => new URL(url, 'http://localhost').searchParams);
}

describe('OrdersPage role gating', () => {
  it('hides every mutating control from a viewer', async () => {
    setup('VIEWER');
    expect(await screen.findByText('ORD-7')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /new order/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('group', { name: /transitions/i })).not.toBeInTheDocument();
    expect(screen.getByText('Read only')).toBeInTheDocument();
  });

  it('offers an operator only the legal transitions and no create or edit', async () => {
    setup('OPERATOR');
    const group = await screen.findByRole('group', { name: /transitions for ORD-7/i });
    const buttons = within(group)
      .getAllByRole('button')
      .map((b) => b.textContent);
    expect(buttons).toEqual(['Complete', 'Cancel']);
    expect(screen.queryByRole('button', { name: /new order/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /edit ORD-7/i })).not.toBeInTheDocument();
  });

  it('lets an engineer create orders but not edit one that is in progress', async () => {
    setup('ENGINEER');
    expect(await screen.findByRole('button', { name: /new order/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /edit ORD-7/i })).not.toBeInTheDocument();
  });
});

describe('OrdersPage paging', () => {
  it('requests the first page of 50 and shows the range from the envelope total', async () => {
    const fetchMock = setup('VIEWER', 120);
    expect(await screen.findByText('Showing 1 to 50 of 120')).toBeInTheDocument();
    const [first] = orderRequests(fetchMock);
    expect(first.get('limit')).toBe('50');
    expect(first.get('offset')).toBe('0');
    expect(first.has('status')).toBe(false);
  });

  it('requests offset 50 when the next page is clicked and keeps the previous rows visible', async () => {
    const fetchMock = setup('VIEWER', 120);
    const user = userEvent.setup();
    await screen.findByText('ORD-7');
    await user.click(screen.getByRole('button', { name: 'Next page' }));
    expect(screen.getByText('ORD-7')).toBeInTheDocument();
    expect(await screen.findByText('Showing 51 to 100 of 120')).toBeInTheDocument();
    const last = orderRequests(fetchMock).at(-1);
    expect(last?.get('offset')).toBe('50');
    expect(last?.get('limit')).toBe('50');
  });

  it('returns to offset 0 when the status filter changes', async () => {
    const fetchMock = setup('VIEWER', 120);
    const user = userEvent.setup();
    await screen.findByText('ORD-7');
    await user.click(screen.getByRole('button', { name: 'Next page' }));
    await screen.findByText('Showing 51 to 100 of 120');
    await user.selectOptions(screen.getByLabelText('Status filter'), 'COMPLETED');
    await screen.findByText('Showing 1 to 50 of 120');
    const last = orderRequests(fetchMock).at(-1);
    expect(last?.get('status')).toBe('COMPLETED');
    expect(last?.get('offset')).toBe('0');
  });

  it('renders no pager when the list is empty', async () => {
    mockFetch([[/\/production-orders/, () => pageResponse([], 0)]]);
    renderWithProviders(<OrdersPage />, { user: makeUser('VIEWER') });
    expect(await screen.findByText('No orders match this filter')).toBeInTheDocument();
    expect(screen.queryByRole('navigation', { name: /pagination/i })).not.toBeInTheDocument();
  });
});
