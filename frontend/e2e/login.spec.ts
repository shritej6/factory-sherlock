import { expect, test } from '@playwright/test';

import { signIn } from './support/auth';

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
    await signIn(page, 'engineer');

    await expect(page).toHaveURL(/\/$/);
    const sidebar = page.getByRole('complementary', { name: 'Primary' });
    await expect(sidebar.getByRole('link')).toHaveText(SECTIONS);
    await expect(sidebar.getByText('engineer', { exact: true })).toBeVisible();
    await expect(sidebar.getByText('Engineer', { exact: true })).toBeVisible();
  });
});
