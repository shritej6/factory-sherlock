import { expect, test } from '@playwright/test';

import { signIn } from './support/auth';

const QUERY = 'batches_requiring_review';

test('the SQL explorer runs batches_requiring_review and shows rows and the SQL', async ({
  page,
}) => {
  await signIn(page, 'engineer');
  await page.goto('/analytics');

  const explorer = page.getByRole('region', { name: 'SQL explorer' });
  await explorer.getByLabel('Query').selectOption(QUERY);
  await explorer.getByRole('button', { name: 'Run query' }).click();

  await expect(explorer.getByText(/returned [1-9]\d* row\(s\)\./)).toBeVisible();
  const table = explorer.getByRole('table', { name: `Rows returned by ${QUERY}` });
  await expect(table.getByRole('columnheader', { name: 'batch number' })).toBeVisible();
  await expect(
    table
      .getByRole('row')
      .filter({ has: page.getByRole('cell') })
      .first(),
  ).toBeVisible();

  await explorer.getByRole('button', { name: 'Show the SQL' }).click();
  await expect(explorer.getByText(/^Query name:/)).toContainText(QUERY);
  await expect(explorer.getByText(/^Parameters:/)).toContainText('threshold=');
  await expect(explorer.locator('pre')).toContainText('SELECT');
  await expect(explorer.getByRole('button', { name: 'Hide the SQL' })).toBeVisible();
});
