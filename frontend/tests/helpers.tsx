import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render } from '@testing-library/react';
import type { ReactElement } from 'react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { vi } from 'vitest';

import { StaticAuthProvider } from '@/hooks/AuthProvider';
import type { User, UserRole } from '@/types/api';

export function makeUser(role: UserRole): User {
  return {
    id: 1,
    username: role.toLowerCase(),
    email: `${role.toLowerCase()}@example.com`,
    role,
    is_active: true,
  };
}

export function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

type Handler = (url: string, init?: RequestInit) => Response | Promise<Response>;

/** Installs a fetch mock that routes by regular expression; unmatched calls return an empty list. */
export function mockFetch(routes: Array<[RegExp, Handler]>): ReturnType<typeof vi.fn> {
  const fn = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url =
      typeof input === 'string' ? input : input instanceof URL ? input.toString() : input.url;
    const match = routes.find(([pattern]) => pattern.test(url));
    if (match) return match[1](url, init);
    return jsonResponse([]);
  });
  vi.stubGlobal('fetch', fn);
  return fn;
}

interface RenderOptions {
  user?: User | null;
  route?: string;
  path?: string;
}

export function renderWithProviders(
  ui: ReactElement,
  { user = makeUser('ENGINEER'), route = '/', path = '*' }: RenderOptions = {},
) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <StaticAuthProvider value={{ user }}>
        <MemoryRouter initialEntries={[route]}>
          <Routes>
            <Route path={path} element={ui} />
          </Routes>
        </MemoryRouter>
      </StaticAuthProvider>
    </QueryClientProvider>,
  );
}
