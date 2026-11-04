import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import type { Evidence } from '@/types/api';

import { EvidenceCard } from './EvidenceCard';

const evidence: Evidence = {
  id: 11,
  sequence: 1,
  rule_code: 'R1',
  title: 'Machine defect-rate comparison',
  narrative: 'CNC-03 failed 46 of 480 inspections (9.6%), rank 1 of 3 machines.',
  query_name: 'machine_defect_rate_comparison',
  query_sql: 'SELECT machine_code, defect_rate FROM ...',
  result_rows: [
    {
      machine_code: 'CNC-03',
      inspected: 480,
      failed: 46,
      defect_rate: 0.0958,
      started_at: '2026-11-02T11:30:00',
    },
    { machine_code: 'CNC-02', inspected: 440, failed: 3, defect_rate: 0.0068, started_at: null },
  ],
};

describe('EvidenceCard', () => {
  it('renders the rule code, title, narrative, formatted rows, and SQL disclosure', async () => {
    render(<EvidenceCard evidence={evidence} />);
    const card = screen.getByRole('article', { name: /machine defect-rate comparison/i });
    expect(within(card).getByText('R1')).toBeInTheDocument();
    expect(within(card).getByText(/failed 46 of 480 inspections/)).toBeInTheDocument();
    expect(within(card).getByText('2 row(s)')).toBeInTheDocument();

    const table = within(card).getByRole('table');
    expect(
      within(table)
        .getAllByRole('columnheader')
        .map((h) => h.textContent),
    ).toEqual(['machine code', 'inspected', 'failed', 'defect rate', 'started at']);
    expect(within(table).getByText('9.6%')).toBeInTheDocument();
    expect(within(table).getByText('2026-11-02 11:30')).toBeInTheDocument();
    expect(within(table).getByText('null')).toBeInTheDocument();

    await userEvent.click(within(card).getByRole('button', { name: 'Show the SQL' }));
    expect(within(card).getByText('machine_defect_rate_comparison')).toBeInTheDocument();
    expect(within(card).getByText(/SELECT machine_code, defect_rate/)).toBeInTheDocument();
  });

  it('shows an empty state when a rule returned no rows', () => {
    render(<EvidenceCard evidence={{ ...evidence, result_rows: [] }} />);
    expect(screen.getByText('This rule returned no rows')).toBeInTheDocument();
  });
});
