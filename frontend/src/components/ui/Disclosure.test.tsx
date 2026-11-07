import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { Button } from './Button';
import { Disclosure } from './Disclosure';

function renderDisclosure() {
  return render(
    <Disclosure label="New order">
      {(close) => (
        <form aria-label="Create order">
          <Button onClick={close}>Cancel</Button>
        </form>
      )}
    </Disclosure>,
  );
}

describe('Disclosure', () => {
  it('exposes the expanded state and the controlled region', async () => {
    const user = userEvent.setup();
    renderDisclosure();
    const toggle = screen.getByRole('button', { name: 'New order' });
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByRole('form', { name: 'Create order' })).not.toBeInTheDocument();

    await user.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    expect(toggle).toHaveTextContent('Cancel');
    const region = screen.getByRole('form', { name: 'Create order' }).parentElement;
    expect(region).toHaveAttribute('id', toggle.getAttribute('aria-controls'));
  });

  it('returns focus to the toggle when the form closes itself', async () => {
    const user = userEvent.setup();
    renderDisclosure();
    const toggle = screen.getByRole('button', { name: 'New order' });
    await user.click(toggle);
    const form = screen.getByRole('form', { name: 'Create order' });
    await user.click(within(form).getByRole('button', { name: 'Cancel' }));
    expect(screen.queryByRole('form', { name: 'Create order' })).not.toBeInTheDocument();
    expect(toggle).toHaveTextContent('New order');
    expect(toggle).toHaveFocus();
  });

  it('is operable from the keyboard', async () => {
    const user = userEvent.setup();
    renderDisclosure();
    await user.tab();
    expect(screen.getByRole('button', { name: 'New order' })).toHaveFocus();
    await user.keyboard('{Enter}');
    expect(screen.getByRole('form', { name: 'Create order' })).toBeInTheDocument();
  });
});
