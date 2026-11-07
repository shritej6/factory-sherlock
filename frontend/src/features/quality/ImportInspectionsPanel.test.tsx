import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { jsonResponse, makeUser, mockFetch, renderWithProviders } from '@tests/helpers';

import { ImportInspectionsPanel, MAX_IMPORT_BYTES } from './ImportInspectionsPanel';

const csvFile = new File(['serial_number,characteristic,measured_value\n'], 'inspections.csv', {
  type: 'text/csv',
});

const IMPORT_ROUTE = /\/inspections\/import$/;

async function openPanel(role: 'OPERATOR' | 'ENGINEER' = 'OPERATOR') {
  renderWithProviders(<ImportInspectionsPanel />, { user: makeUser(role) });
  await userEvent.click(screen.getByRole('button', { name: 'Import inspections from CSV' }));
  return {
    input: screen.getByLabelText('CSV file') as HTMLInputElement,
    importButton: screen.getByRole('button', { name: 'Import' }),
  };
}

describe('ImportInspectionsPanel', () => {
  it('shows no import control to a viewer', () => {
    mockFetch([]);
    renderWithProviders(<ImportInspectionsPanel />, { user: makeUser('VIEWER') });
    expect(
      screen.queryByRole('button', { name: /import inspections from csv/i }),
    ).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Import' })).not.toBeInTheDocument();
  });

  it('enables the import button once a file is chosen', async () => {
    mockFetch([]);
    const { input, importButton } = await openPanel();
    expect(importButton).toBeDisabled();
    await userEvent.upload(input, csvFile);
    expect(importButton).toBeEnabled();
  });

  it('posts the chosen file as multipart and shows the import summary', async () => {
    const fetchMock = mockFetch([
      [
        IMPORT_ROUTE,
        () => jsonResponse({ imported: 18, failed_inspections: 3, inspection_ids: [1, 2, 3] }, 201),
      ],
    ]);
    const { input, importButton } = await openPanel('ENGINEER');
    await userEvent.upload(input, csvFile);
    await userEvent.click(importButton);

    expect(
      await screen.findByText('Imported 18 inspections, 3 failed the specification.'),
    ).toBeInTheDocument();

    const call = fetchMock.mock.calls.find(([url]) => IMPORT_ROUTE.test(String(url)));
    expect(call).toBeDefined();
    const init = call?.[1] as RequestInit;
    expect(init.method).toBe('POST');
    expect(init.body).toBeInstanceOf(FormData);
    expect((init.body as FormData).get('file')).toBe(csvFile);
    expect((init.headers as Record<string, string>)['Content-Type']).toBeUndefined();
    expect(screen.getByRole('button', { name: 'Import' })).toBeDisabled();
  });

  it('lists every row error from a 422 and keeps the file for a retry', async () => {
    mockFetch([
      [
        IMPORT_ROUTE,
        () =>
          jsonResponse(
            {
              error: 'ValidationError',
              message: 'The CSV failed validation',
              details: {
                errors: [
                  { row: 2, field: 'measured_value', message: 'must be a number' },
                  { row: 5, field: null, message: 'unit SN-500 does not exist' },
                ],
              },
              request_id: 'req-1',
            },
            422,
          ),
      ],
    ]);
    const { input, importButton } = await openPanel();
    await userEvent.upload(input, csvFile);
    await userEvent.click(importButton);

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'The CSV failed validation. Fix the rows below and import the file again.',
    );
    const table = screen.getByRole('table', { name: 'Import errors by row' });
    const rows = within(table).getAllByRole('row').slice(1);
    expect(rows).toHaveLength(2);
    expect(rows[0]).toHaveTextContent('2');
    expect(rows[0]).toHaveTextContent('measured_value');
    expect(rows[0]).toHaveTextContent('must be a number');
    expect(rows[1]).toHaveTextContent('5');
    expect(rows[1]).toHaveTextContent('whole row');
    expect(rows[1]).toHaveTextContent('unit SN-500 does not exist');

    expect(input.files?.[0]?.name).toBe('inspections.csv');
    expect(importButton).toBeEnabled();
  });

  it('blocks a file over 1 MiB before any request is made', async () => {
    const fetchMock = mockFetch([]);
    const { input, importButton } = await openPanel();
    const oversized = new File([new Uint8Array(MAX_IMPORT_BYTES + 1)], 'big.csv', {
      type: 'text/csv',
    });
    await userEvent.upload(input, oversized);

    expect(screen.getByRole('alert')).toHaveTextContent(
      'big.csv is 1.0 MiB; the limit is 1 MiB. Split the file and import each part.',
    );
    expect(importButton).toBeDisabled();
    expect(fetchMock.mock.calls.some(([url]) => IMPORT_ROUTE.test(String(url)))).toBe(false);
  });
});
