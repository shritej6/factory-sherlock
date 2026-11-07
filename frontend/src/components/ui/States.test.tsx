import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { ApiError } from '@/services/http';

import { ErrorNotice, ErrorState } from './States';

const failure = new ApiError(409, {
  error: 'ConflictError',
  message: 'Batch 12 is already quarantined',
  details: {},
  request_id: 'req-409',
});

describe('ErrorNotice', () => {
  it('announces the backend message and the request id like ErrorState does', () => {
    render(<ErrorNotice error={failure} />);
    const alert = screen.getByRole('alert');
    expect(alert).toHaveTextContent('Batch 12 is already quarantined');
    expect(alert).toHaveTextContent('Request id req-409');
  });

  it('lets the caller replace the sentence but still shows the request id', () => {
    render(<ErrorNotice error={failure}>Fix the rows below.</ErrorNotice>);
    const alert = screen.getByRole('alert');
    expect(alert).toHaveTextContent('Fix the rows below.');
    expect(alert).not.toHaveTextContent('already quarantined');
    expect(alert).toHaveTextContent('Request id req-409');
  });

  it('shows plain errors without a request id line', () => {
    render(<ErrorNotice error={new Error('Every material line needs a lot and a quantity.')} />);
    const alert = screen.getByRole('alert');
    expect(alert).toHaveTextContent('Every material line needs a lot and a quantity.');
    expect(alert).not.toHaveTextContent('Request id');
  });
});

describe('ErrorState', () => {
  it('shows the title, the message and the request id', () => {
    render(<ErrorState error={failure} title="Could not load batches" />);
    const alert = screen.getByRole('alert');
    expect(alert).toHaveTextContent('Could not load batches');
    expect(alert).toHaveTextContent('Batch 12 is already quarantined');
    expect(alert).toHaveTextContent('Request id req-409');
  });
});
