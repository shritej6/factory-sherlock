import { expect, test } from '@playwright/test';

import { signInThroughForm } from './support/auth';

/** The nine sections of frontend/src/app/nav.ts, in sidebar order. */
const SECTIONS = [
  'Factory Overview',
  'Machine Monitoring',
  'Production Orders',
  'Production Batches',
  'Quality Inspection',
  'Investigations',
  'Material Traceability',
  'Analytics and Reports',
  'Simulation',
];

// This is the one spec that types the real demo password into the form; a trace would
// record the typed value and the request body, so none is kept here even on a retry.
// Playwright only accepts a trace override at file level, outside any describe group.
test.use({ trace: 'off' });

test.describe('login', () => {
  test('a wrong password shows the error and stays on the login page', async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel('Username').fill('engineer');
    await page.getByLabel('Password').fill('not-the-demo-password');
    await page.getByRole('button', { name: 'Sign in' }).click();

    await expect(page.getByText('Invalid username or password')).toBeVisible();
    await expect(page).toHaveURL(/\/login$/);
    await expect(page.getByRole('heading', { name: 'Factory Sherlock' })).toBeVisible();
  });

  test('the engineer lands on the overview and the sidebar lists the nine sections', async ({
    page,
  }) => {
    await signInThroughForm(page, 'engineer');

    await expect(page).toHaveURL(/\/$/);
    const sidebar = page.getByRole('complementary', { name: 'Sidebar' });
    await expect(sidebar.getByRole('navigation', { name: 'Primary' }).getByRole('link')).toHaveText(
      SECTIONS,
    );
    await expect(sidebar.getByText('engineer', { exact: true })).toBeVisible();
    await expect(sidebar.getByText('Engineer', { exact: true })).toBeVisible();
  });
});
