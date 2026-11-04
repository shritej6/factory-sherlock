import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { tokenStore } from '@/services/http';
import { jsonResponse, mockFetch } from '@tests/helpers';

import { AuthProvider } from './AuthProvider';
import { useAuth } from './useAuth';

function Probe() {
  const { status, retryRestore } = useAuth();
  return (
    <div>
      <p>status:{status}</p>
      <button type="button" onClick={retryRestore}>
        retry
      </button>
    </div>
  );
}

function renderProbe() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <AuthProvider>
        <Probe />
      </AuthProvider>
    </QueryClientProvider>,
  );
}

describe('AuthProvider session restore', () => {
  it('keeps the token and reports an error when the server cannot be reached, then retries', async () => {
    tokenStore.set('stored-token');
    let attempts = 0;
    mockFetch([
      [
        /\/auth\/me$/,
        () => {
          attempts += 1;
          return attempts === 1
            ? jsonResponse(
                {
                  error: 'DatabaseUnavailable',
                  message: 'The database is not reachable',
                  details: {},
                },
                503,
              )
            : jsonResponse({
                id: 1,
                username: 'viewer',
                email: 'v@example.com',
                role: 'VIEWER',
                is_active: true,
              });
        },
      ],
    ]);
    renderProbe();
    expect(await screen.findByText('status:error')).toBeInTheDocument();
    expect(tokenStore.get()).toBe('stored-token');
    await userEvent.click(screen.getByRole('button', { name: 'retry' }));
    expect(await screen.findByText('status:authenticated')).toBeInTheDocument();
  });

  it('logs out and clears the token when the server rejects it', async () => {
    tokenStore.set('expired-token');
    mockFetch([
      [
        /\/auth\/me$/,
        () =>
          jsonResponse(
            { error: 'AuthenticationError', message: 'Access token is invalid', details: {} },
            401,
          ),
      ],
    ]);
    renderProbe();
    expect(await screen.findByText('status:anonymous')).toBeInTheDocument();
    expect(tokenStore.get()).toBeNull();
  });
});
