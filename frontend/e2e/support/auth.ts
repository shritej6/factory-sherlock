import { expect, test } from '@playwright/test';
import type { APIRequestContext, Page } from '@playwright/test';

export type DemoAccount = 'admin' | 'engineer' | 'operator' | 'viewer';

/** Relative to baseURL, so API calls go through the Vite proxy like the app's own fetches. */
export const API = '/api/v1';

/** Where the app keeps its bearer token; must match TOKEN_KEY in frontend/src/services/http.ts. */
const TOKEN_KEY = 'factory-sherlock.token';

function password(): string {
  const value = process.env.E2E_PASSWORD;
  if (!value) throw new Error('E2E_PASSWORD is not set; playwright.config.ts resolves it.');
  return value;
}

/**
 * Waits for the signed-in app or for the first alert, whichever appears first, and fails with
 * the alert text so a wrong password or a throttled account is reported in one line instead
 * of as an expect timeout.
 */
async function expectSignedIn(page: Page, account: DemoAccount): Promise<void> {
  const heading = page.getByRole('heading', { name: 'Factory Overview' });
  const alert = page.getByRole('alert');
  await expect(heading.or(alert).first()).toBeVisible();
  if (await heading.isVisible()) return;
  const text = (await alert.first().innerText()).replace(/\s+/g, ' ').trim();
  throw new Error(`Sign in as ${account} failed: ${text}`);
}

/**
 * Logs in over Node's fetch, outside the browser context, so the password is never part of a
 * Playwright trace (traces record typed values and request bodies). The returned token is
 * short-lived and is the only credential the trace can hold.
 */
async function fetchToken(account: DemoAccount): Promise<string> {
  const baseURL = test.info().project.use.baseURL;
  if (!baseURL) throw new Error('baseURL is not configured; see playwright.config.ts.');
  const response = await fetch(new URL(`${API}/auth/login`, baseURL), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({ username: account, password: password() }),
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { message?: string };
    throw new Error(
      `Login as ${account} returned ${response.status}: ${body.message ?? 'no message'}`,
    );
  }
  const body = (await response.json()) as { access_token: string };
  return body.access_token;
}

/**
 * Signs in by storing a token where the app keeps it and letting the app restore the session
 * on load, then waits for the overview. Use signInThroughForm only where the form itself is
 * under test.
 */
export async function signIn(page: Page, account: DemoAccount): Promise<void> {
  const token = await fetchToken(account);
  await page.goto('/login');
  await page.evaluate(([key, value]) => window.localStorage.setItem(key, value), [
    TOKEN_KEY,
    token,
  ] as const);
  await page.goto('/');
  await expectSignedIn(page, account);
}

/**
 * Signs in through the login form, typing the password. Call it only from a spec that turns
 * tracing off (login.spec.ts does), because a trace records the typed value and the request.
 */
export async function signInThroughForm(page: Page, account: DemoAccount): Promise<void> {
  await page.goto('/login');
  await page.getByLabel('Username').fill(account);
  await page.getByLabel('Password').fill(password());
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expectSignedIn(page, account);
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
