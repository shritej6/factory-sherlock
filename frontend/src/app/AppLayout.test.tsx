import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { describe, expect, it } from 'vitest';

import { StaticAuthProvider } from '@/hooks/AuthProvider';
import type { Machine } from '@/types/api';
import { jsonResponse, makeUser, mockFetch } from '@tests/helpers';

import { AppLayout } from './AppLayout';

const machines: Machine[] = [
  {
    id: 1,
    code: 'CNC-01',
    name: 'CNC Machine 01',
    status: 'RUNNING',
    updated_at: '2026-11-07T16:41:00',
  },
  {
    id: 3,
    code: 'CNC-03',
    name: 'CNC Machine 03',
    status: 'FAULT',
    updated_at: '2026-11-07T16:41:00',
  },
];

function renderLayout(route = '/orders') {
  mockFetch([[/\/machines$/, () => jsonResponse(machines)]]);
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <StaticAuthProvider value={{ user: makeUser('ENGINEER') }}>
        <MemoryRouter initialEntries={[route]}>
          <Routes>
            <Route element={<AppLayout />}>
              <Route path="/" element={<p>Overview body</p>} />
              <Route path="/orders" element={<p>Orders body</p>} />
            </Route>
          </Routes>
        </MemoryRouter>
      </StaticAuthProvider>
    </QueryClientProvider>,
  );
}

describe('AppLayout', () => {
  it('offers a skip link that targets the main landmark', () => {
    renderLayout();
    const skip = screen.getByRole('link', { name: 'Skip to content' });
    expect(skip).toHaveAttribute('href', '#main');
    expect(screen.getByRole('main')).toHaveAttribute('id', 'main');
  });

  it('marks the current page on the soft-key bar and no other key', () => {
    renderLayout('/orders');
    const nav = screen.getByRole('navigation', { name: 'Primary' });
    const current = within(nav).getByRole('link', { name: 'Production Orders' });
    expect(current).toHaveAttribute('aria-current', 'page');
    const marked = within(nav)
      .getAllByRole('link')
      .filter((link) => link.hasAttribute('aria-current'));
    expect(marked).toEqual([current]);
  });

  it('shows every machine with its state in the status band, plus the signed-in user', async () => {
    renderLayout();
    const band = screen.getByRole('banner');
    const states = within(band).getByRole('list', { name: 'Machine states' });
    const items = await within(states).findAllByRole('listitem');
    expect(items.map((item) => item.textContent)).toEqual(['CNC-01RUNNING', 'CNC-03FAULT']);
    expect(within(band).getByText('engineer')).toBeInTheDocument();
    expect(within(band).getByText('Engineer')).toBeInTheDocument();
    expect(within(band).getByRole('button', { name: 'Sign out' })).toBeInTheDocument();
  });
});
