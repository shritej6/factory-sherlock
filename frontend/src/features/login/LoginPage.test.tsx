import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router';
import { describe, expect, it } from 'vitest';

import { AppProviders } from '@/app/providers';
import { tokenStore } from '@/services/http';
import { jsonResponse, mockFetch } from '@tests/helpers';

import { LoginPage } from './LoginPage';

function renderLogin() {
  return render(
    <AppProviders>
      <MemoryRouter initialEntries={['/login']}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<h1>Overview home</h1>} />
        </Routes>
      </MemoryRouter>
    </AppProviders>,
  );
}

describe('LoginPage', () => {
  it('posts credentials, stores the token, and navigates to the overview', async () => {
    const fetchMock = mockFetch([
      [
        /\/api\/v1\/auth\/login$/,
        () =>
          jsonResponse({
            access_token: 'token-123',
            token_type: 'bearer',
            expires_in_minutes: 120,
          }),
      ],
      [
        /\/api\/v1\/auth\/me$/,
        () =>
          jsonResponse({
            id: 2,
            username: 'engineer',
            email: 'e@example.com',
            role: 'ENGINEER',
            is_active: true,
          }),
      ],
    ]);
    renderLogin();
    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/username/i), 'engineer');
    await user.type(screen.getByLabelText(/password/i), 'secret');
    await user.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => expect(screen.getByText('Overview home')).toBeInTheDocument());
    expect(tokenStore.get()).toBe('token-123');
    const loginCall = fetchMock.mock.calls.find(([url]) => String(url).endsWith('/auth/login'));
    expect(loginCall).toBeDefined();
    expect(JSON.parse(String(loginCall?.[1]?.body))).toEqual({
      username: 'engineer',
      password: 'secret',
    });
    const meCall = fetchMock.mock.calls.find(([url]) => String(url).endsWith('/auth/me'));
    expect((meCall?.[1]?.headers as Record<string, string>).Authorization).toBe('Bearer token-123');
  });

  it('shows the API message when credentials are rejected', async () => {
    mockFetch([
      [
        /\/auth\/login$/,
        () =>
          jsonResponse(
            { error: 'AuthenticationError', message: 'Invalid username or password', details: {} },
            401,
          ),
      ],
    ]);
    renderLogin();
    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/username/i), 'viewer');
    await user.type(screen.getByLabelText(/password/i), 'wrong');
    await user.click(screen.getByRole('button', { name: /sign in/i }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid username or password');
    expect(tokenStore.get()).toBeNull();
  });
});
