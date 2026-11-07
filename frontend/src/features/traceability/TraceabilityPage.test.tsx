import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { jsonResponse, makeUser, mockFetch, renderWithProviders } from '@tests/helpers';

import { TraceabilityPage } from './TraceabilityPage';

describe('TraceabilityPage', () => {
  it('shows prompts before any search and hides the quarantine form from viewers', () => {
    mockFetch([]);
    renderWithProviders(<TraceabilityPage />, { user: makeUser('VIEWER') });
    expect(screen.getByText('Enter a lot number to begin')).toBeInTheDocument();
    expect(screen.getByText('Enter a serial number to begin')).toBeInTheDocument();
    expect(
      screen.queryByRole('form', { name: /quarantine material lot/i }),
    ).not.toBeInTheDocument();
    expect(screen.getByText(/can quarantine lots/)).toBeInTheDocument();
  });

  it('shows a not-found empty state when the lot does not exist', async () => {
    mockFetch([
      [
        /\/traceability\/forward\/UNKNOWN$/,
        () =>
          jsonResponse(
            { error: 'NotFoundError', message: 'Material lot UNKNOWN not found', details: {} },
            404,
          ),
      ],
    ]);
    renderWithProviders(<TraceabilityPage />);
    await userEvent.type(screen.getByLabelText(/lot number/i), 'UNKNOWN');
    await userEvent.click(screen.getByRole('button', { name: 'Trace lot' }));
    expect(await screen.findByText('Lot UNKNOWN was not found')).toBeInTheDocument();
  });

  it('shows the consuming batches for a known lot', async () => {
    mockFetch([
      [
        /\/traceability\/forward\/L201$/,
        () =>
          jsonResponse({
            lot_number: 'L201',
            batches: [
              {
                lot_number: 'L201',
                material_name: 'Steel',
                supplier: 'Northline',
                lot_status: 'AVAILABLE',
                batch_id: 24,
                batch_number: 'ORD-1-B01',
                batch_status: 'COMPLETED',
                started_at: '2026-11-02T06:00:00',
                machine_code: 'CNC-03',
                order_number: 'ORD-1',
                product_name: 'Shaft',
                quantity_used: 20,
                units_produced: 20,
                units_failed: 1,
              },
            ],
          }),
      ],
    ]);
    renderWithProviders(<TraceabilityPage />);
    await userEvent.type(screen.getByLabelText(/lot number/i), 'L201');
    await userEvent.click(screen.getByRole('button', { name: 'Trace lot' }));
    expect(await screen.findByText('ORD-1-B01')).toBeInTheDocument();
    expect(screen.getByText('1 (5.0%)')).toBeInTheDocument();
  });

  it('refreshes an open forward trace after a lot is quarantined', async () => {
    const lot = {
      id: 1,
      lot_number: 'L201',
      material_name: 'Steel',
      supplier: 'Northline',
      quantity_received: '500',
      status: 'AVAILABLE',
      received_at: '2026-11-01T08:00:00',
    };
    const fetchMock = mockFetch([
      [
        /\/traceability\/material-lots\/1\/quarantine$/,
        () => jsonResponse({ lot: { ...lot, status: 'QUARANTINED' }, quarantined_batches: [] }),
      ],
      [/\/material-lots$/, () => jsonResponse([lot])],
      [/\/traceability\/forward\/L201$/, () => jsonResponse({ lot_number: 'L201', batches: [] })],
    ]);
    renderWithProviders(<TraceabilityPage />);
    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/^lot number/i), 'L201');
    await user.click(screen.getByRole('button', { name: 'Trace lot' }));
    expect(
      await screen.findByText('Lot L201 has not been consumed by any batch'),
    ).toBeInTheDocument();
    const forwardCalls = () =>
      fetchMock.mock.calls.filter(([input]) => /\/traceability\/forward\//.test(String(input)))
        .length;
    expect(forwardCalls()).toBe(1);

    await user.selectOptions(await screen.findByRole('combobox', { name: /material lot/i }), '1');
    await user.type(screen.getByLabelText(/reason/i), 'Supplier recall');
    await user.click(screen.getByRole('button', { name: 'Quarantine lot and its batches' }));

    expect(await screen.findByText(/Lot L201 is quarantined/)).toBeInTheDocument();
    await waitFor(() => expect(forwardCalls()).toBe(2));
  });
});
