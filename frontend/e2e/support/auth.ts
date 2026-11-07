import { expect } from '@playwright/test';
import type { APIRequestContext, Page } from '@playwright/test';

export type DemoAccount = 'admin' | 'engineer' | 'operator' | 'viewer';

/** Relative to baseURL, so API calls go through the Vite proxy like the app's own fetches. */
export const API = '/api/v1';

function password(): string {
  const value = process.env.E2E_PASSWORD;
  if (!value) throw new Error('E2E_PASSWORD is not set; playwright.config.ts resolves it.');
  return value;
}

/** Signs in through the login form and waits for the overview to render. */
export async function signIn(page: Page, account: DemoAccount): Promise<void> {
  await page.goto('/login');
  await page.getByLabel('Username').fill(account);
  await page.getByLabel('Password').fill(password());
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page.getByRole('heading', { name: 'Factory Overview' })).toBeVisible();
}

/** Signs in through the API and returns the bearer token for direct requests. */
export async function apiToken(request: APIRequestContext, account: DemoAccount): Promise<string> {
  const response = await request.post(`${API}/auth/login`, {
    data: { username: account, password: password() },
  });
  expect(response.ok(), `login as ${account} returned ${response.status()}`).toBeTruthy();
  const body = (await response.json()) as { access_token: string };
  return body.access_token;
}

export function bearer(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}` };
}

/** GET a JSON resource with the token, failing the test on any non-2xx status. */
export async function apiGet<T>(
  request: APIRequestContext,
  token: string,
  path: string,
  params?: Record<string, string | number>,
): Promise<T> {
  const response = await request.get(`${API}${path}`, { headers: bearer(token), params });
  expect(response.ok(), `GET ${path} returned ${response.status()}`).toBeTruthy();
  return (await response.json()) as T;
}
