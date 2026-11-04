import { screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import type { ProductionOrder } from '@/types/api';
import { jsonResponse, makeUser, mockFetch, renderWithProviders } from '@tests/helpers';

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

function setup(role: 'VIEWER' | 'OPERATOR' | 'ENGINEER') {
  mockFetch([[/\/production-orders/, () => jsonResponse([order])]]);
  return renderWithProviders(<OrdersPage />, { user: makeUser(role) });
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
