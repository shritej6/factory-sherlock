import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router';
import { describe, expect, it } from 'vitest';

import { StaticAuthProvider } from '@/hooks/AuthProvider';
import { makeUser } from '@tests/helpers';

import { AppLayout } from './AppLayout';

function renderLayout(route = '/orders') {
  return render(
    <StaticAuthProvider value={{ user: makeUser('ENGINEER') }}>
      <MemoryRouter initialEntries={[route]}>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path="/" element={<p>Overview body</p>} />
            <Route path="/orders" element={<p>Orders body</p>} />
          </Route>
        </Routes>
      </MemoryRouter>
    </StaticAuthProvider>,
  );
}

describe('AppLayout', () => {
  it('offers a skip link that targets the main landmark', () => {
    renderLayout();
    const skip = screen.getByRole('link', { name: 'Skip to content' });
    expect(skip).toHaveAttribute('href', '#main');
    expect(screen.getByRole('main')).toHaveAttribute('id', 'main');
  });

  it('marks the current page in the primary navigation and no other item', () => {
    renderLayout('/orders');
    const nav = screen.getByRole('navigation', { name: 'Primary' });
    const current = within(nav).getByRole('link', { name: 'Production Orders' });
    expect(current).toHaveAttribute('aria-current', 'page');
    const marked = within(nav)
      .getAllByRole('link')
      .filter((link) => link.hasAttribute('aria-current'));
    expect(marked).toEqual([current]);
  });

  it('moves focus into the drawer when it opens and back to the menu button on Escape', async () => {
    const user = userEvent.setup();
    renderLayout();
    const menu = screen.getByRole('button', { name: 'Menu' });
    expect(menu).toHaveAttribute('aria-expanded', 'false');
    expect(menu).toHaveAttribute('aria-controls', 'primary-navigation');

    await user.click(menu);
    expect(menu).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByRole('link', { name: 'Factory Overview' })).toHaveFocus();

    await user.keyboard('{Escape}');
    expect(menu).toHaveAttribute('aria-expanded', 'false');
    expect(menu).toHaveFocus();
  });
});
