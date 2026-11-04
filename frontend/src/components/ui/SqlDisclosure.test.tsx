import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { SqlDisclosure } from './SqlDisclosure';

const SQL = 'SELECT m.code, COUNT(*) AS failed\nFROM inspections i\nWHERE i.result = :result';

describe('SqlDisclosure', () => {
  it('hides the SQL until toggled and reveals the query name and parameters', async () => {
    render(
      <SqlDisclosure
        sql={SQL}
        queryName="machine_defect_rate_comparison"
        params={{ window_start: '2026-11-01T00:00:00', machine_id: null }}
      />,
    );
    const toggle = screen.getByRole('button', { name: 'Show the SQL' });
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByText(/FROM inspections/)).not.toBeInTheDocument();

    await userEvent.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    expect(toggle).toHaveTextContent('Hide the SQL');
    expect(screen.getByText(/FROM inspections/)).toBeInTheDocument();
    expect(screen.getByText('machine_defect_rate_comparison')).toBeInTheDocument();
    expect(
      screen.getByText(/window_start=2026-11-01T00:00:00, machine_id=null/),
    ).toBeInTheDocument();

    await userEvent.click(toggle);
    expect(screen.queryByText(/FROM inspections/)).not.toBeInTheDocument();
  });
});
