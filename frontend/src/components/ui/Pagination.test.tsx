import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { Pagination } from './Pagination';

function setup(props: { total: number; limit: number; offset: number }) {
  const onChange = vi.fn();
  render(<Pagination {...props} onChange={onChange} label="Orders" />);
  return onChange;
}

describe('Pagination', () => {
  it('renders nothing when there are no rows', () => {
    setup({ total: 0, limit: 50, offset: 0 });
    expect(screen.queryByRole('navigation')).not.toBeInTheDocument();
  });

  it('describes the visible range and names the list for assistive technology', () => {
    setup({ total: 1230, limit: 50, offset: 100 });
    expect(screen.getByRole('navigation', { name: 'Orders pagination' })).toBeInTheDocument();
    expect(screen.getByText('Showing 101 to 150 of 1,230')).toBeInTheDocument();
  });

  it('clamps the range on the last page', () => {
    setup({ total: 120, limit: 50, offset: 100 });
    expect(screen.getByText('Showing 101 to 120 of 120')).toBeInTheDocument();
  });

  it('clamps back to the last page with rows when the offset runs past the total', () => {
    const onChange = setup({ total: 100, limit: 50, offset: 100 });
    expect(onChange).toHaveBeenCalledTimes(1);
    expect(onChange).toHaveBeenCalledWith({ limit: 50, offset: 50 });
    expect(screen.getByText('Showing 51 to 100 of 100')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Next page' })).toBeDisabled();
  });

  it('returns to the first page when a single remaining row sits before the offset', () => {
    const onChange = setup({ total: 1, limit: 25, offset: 75 });
    expect(onChange).toHaveBeenCalledWith({ limit: 25, offset: 0 });
    expect(screen.getByText('Showing 1 to 1 of 1')).toBeInTheDocument();
  });

  it('leaves a valid offset alone', () => {
    const onChange = setup({ total: 120, limit: 50, offset: 100 });
    expect(onChange).not.toHaveBeenCalled();
  });

  it('disables previous on the first page and next on the last page', () => {
    setup({ total: 120, limit: 50, offset: 0 });
    expect(screen.getByRole('button', { name: 'Previous page' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Next page' })).toBeEnabled();
  });

  it('disables next when the current page reaches the total', () => {
    setup({ total: 120, limit: 50, offset: 100 });
    expect(screen.getByRole('button', { name: 'Previous page' })).toBeEnabled();
    expect(screen.getByRole('button', { name: 'Next page' })).toBeDisabled();
  });

  it('moves by one page in each direction without going below zero', async () => {
    const user = userEvent.setup();
    const onChange = setup({ total: 120, limit: 50, offset: 50 });
    await user.click(screen.getByRole('button', { name: 'Next page' }));
    expect(onChange).toHaveBeenLastCalledWith({ limit: 50, offset: 100 });
    await user.click(screen.getByRole('button', { name: 'Previous page' }));
    expect(onChange).toHaveBeenLastCalledWith({ limit: 50, offset: 0 });
  });

  it('offers 25, 50 and 100 rows and resets the offset when the page size changes', async () => {
    const user = userEvent.setup();
    const onChange = setup({ total: 300, limit: 50, offset: 100 });
    const select = screen.getByLabelText('Rows per page');
    expect(Array.from(select.querySelectorAll('option')).map((o) => o.value)).toEqual([
      '25',
      '50',
      '100',
    ]);
    await user.selectOptions(select, '100');
    expect(onChange).toHaveBeenCalledWith({ limit: 100, offset: 0 });
  });

  it('is operable from the keyboard', async () => {
    const user = userEvent.setup();
    const onChange = setup({ total: 120, limit: 50, offset: 0 });
    await user.tab();
    expect(screen.getByLabelText('Rows per page')).toHaveFocus();
    await user.tab();
    expect(screen.getByRole('button', { name: 'Next page' })).toHaveFocus();
    await user.keyboard('{Enter}');
    expect(onChange).toHaveBeenCalledWith({ limit: 50, offset: 50 });
  });
});
