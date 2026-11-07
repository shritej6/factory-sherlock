import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import type { ProductionBatch } from '@/types/api';
import { jsonResponse, makeUser, mockFetch, renderWithProviders } from '@tests/helpers';

import { BatchActions } from './BatchActions';

const batch: ProductionBatch = {
  id: 12,
  batch_number: 'ORD-1-B03',
  production_order_id: 1,
  machine_id: 1,
  quantity: 20,
  status: 'IN_PROGRESS',
  started_at: '2026-11-02T06:00:00',
  completed_at: null,
  quarantine_reason: null,
  material_links: [],
};

describe('BatchActions', () => {
  it('names every row action after the batch so it is unambiguous out of context', () => {
    mockFetch([]);
    renderWithProviders(<BatchActions batch={batch} onResult={vi.fn()} />, {
      user: makeUser('ENGINEER'),
    });
    expect(screen.getByRole('button', { name: 'Complete batch ORD-1-B03' })).toHaveTextContent(
      'Complete',
    );
    expect(screen.getByRole('button', { name: 'Quarantine batch ORD-1-B03' })).toHaveTextContent(
      'Quarantine',
    );
  });

  it('moves focus into the reason field when quarantine opens and back when it is cancelled', async () => {
    mockFetch([]);
    const user = userEvent.setup();
    renderWithProviders(<BatchActions batch={batch} onResult={vi.fn()} />, {
      user: makeUser('ENGINEER'),
    });
    await user.click(screen.getByRole('button', { name: 'Quarantine batch ORD-1-B03' }));
    expect(screen.getByLabelText(/reason/i)).toHaveFocus();
    expect(screen.getByRole('form', { name: 'Quarantine batch ORD-1-B03' })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Cancel quarantine of batch ORD-1-B03' }));
    expect(screen.queryByRole('form')).not.toBeInTheDocument();
    await vi.waitFor(() =>
      expect(screen.getByRole('button', { name: 'Quarantine batch ORD-1-B03' })).toHaveFocus(),
    );
  });

  it('hands the failure object to the page so the notice can show the request id', async () => {
    mockFetch([
      [
        /\/complete$/,
        () =>
          jsonResponse(
            {
              error: 'InvalidTransitionError',
              message: 'Batch ORD-1-B03 is already complete',
              details: {},
              request_id: 'req-77',
            },
            409,
          ),
      ],
    ]);
    const onResult = vi.fn();
    const user = userEvent.setup();
    renderWithProviders(<BatchActions batch={batch} onResult={onResult} />, {
      user: makeUser('OPERATOR'),
    });
    await user.click(screen.getByRole('button', { name: 'Complete batch ORD-1-B03' }));
    await vi.waitFor(() => expect(onResult).toHaveBeenCalled());
    const [error] = onResult.mock.calls[0] as [{ message: string; requestId: string }];
    expect(error.message).toBe('Batch ORD-1-B03 is already complete');
    expect(error.requestId).toBe('req-77');
  });
});
