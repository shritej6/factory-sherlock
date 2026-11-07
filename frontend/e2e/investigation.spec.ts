import { expect, test } from '@playwright/test';
import type { APIRequestContext } from '@playwright/test';

import { apiGet, apiToken, signIn } from './support/auth';

interface Machine {
  id: number;
  code: string;
}

interface Batch {
  started_at: string;
}

const RULE_CODES = ['R1', 'R2', 'R3', 'R4', 'R5', 'R6'];

/**
 * The demo scenario covers one production day. Read that day from CNC-03's first
 * batch instead of hard-coding it, so a re-seeded scenario keeps the test valid.
 */
async function demoScope(request: APIRequestContext): Promise<{ machineId: number; day: string }> {
  const token = await apiToken(request, 'engineer');
  const machines = await apiGet<Machine[]>(request, token, '/machines');
  const cnc03 = machines.find((machine) => machine.code === 'CNC-03');
  if (!cnc03) throw new Error('The demo data has no machine CNC-03; seed the demo scenario.');
  const batches = await apiGet<Batch[]>(request, token, '/production-batches', {
    machine_id: cnc03.id,
  });
  const starts = batches.map((batch) => batch.started_at).sort();
  if (starts.length === 0) throw new Error('CNC-03 has no batches; seed the demo scenario.');
  return { machineId: cnc03.id, day: starts[0].slice(0, 10) };
}

test('an engineer opens, reviews, and closes an investigation on CNC-03', async ({
  page,
  request,
}) => {
  const { machineId, day } = await demoScope(request);
  const title = `E2E CNC-03 tool wear ${Date.now()}`;

  await signIn(page, 'engineer');
  await page
    .getByRole('complementary', { name: 'Primary' })
    .getByRole('link', { name: 'Investigations' })
    .click();
  await page.getByRole('button', { name: 'Open investigation' }).click();

  const form = page.getByRole('form', { name: 'Open investigation' });
  await form.getByLabel('Title').fill(title);
  await form.getByLabel('Machine').selectOption(String(machineId));
  await form.getByLabel('Window start').fill(`${day}T06:00`);
  await form.getByLabel('Window end').fill(`${day}T12:00`);
  await form.getByRole('button', { name: 'Run the rules and open the case' }).click();

  await expect(page).toHaveURL(/\/investigations\/\d+$/);
  await expect(page.getByRole('heading', { name: title })).toBeVisible();

  const summary = page.getByRole('region', { name: 'Case summary' });
  await expect(summary).toContainText('CNC-03');
  await expect(summary).toContainText('elevated defect rate');
  await expect(summary.getByText('Open', { exact: true })).toBeVisible();

  // The first six cards are R1 to R6 in order; the total is not asserted because
  // further rules may be added.
  const cards = page.getByTestId('evidence-card');
  await expect(cards.first()).toBeVisible();
  for (const [index, code] of RULE_CODES.entries()) {
    await expect(cards.nth(index).getByText(code, { exact: true })).toBeVisible();
  }

  const r1 = cards.nth(0);
  await r1.getByRole('button', { name: 'Show the SQL' }).click();
  await expect(r1.locator('pre')).toContainText('SELECT');
  await expect(r1.getByRole('button', { name: 'Hide the SQL' })).toBeVisible();

  const flagged = page.getByRole('list', { name: 'Flagged batches' });
  await expect(flagged.getByRole('listitem').first()).toBeVisible();

  // Allowed path: OPEN -> IN_REVIEW -> CLOSED, the last step with a conclusion.
  await page.getByRole('button', { name: 'Mark in review' }).click();
  await expect(summary.getByText('In Review', { exact: true })).toBeVisible();

  await page.getByRole('button', { name: 'Close with conclusion' }).click();
  const closeForm = page.getByRole('form', { name: 'Close investigation' });
  await closeForm
    .getByLabel('Conclusion')
    .fill('Browser test: tool wear on CNC-03 confirmed by the rules; batches left for review.');
  await closeForm.getByRole('button', { name: 'Close case' }).click();

  await expect(summary.getByText('Closed', { exact: true })).toBeVisible();
  await expect(summary.getByRole('heading', { name: 'Engineer conclusion' })).toBeVisible();
  await expect(page.getByText('This case is closed and cannot be reopened.')).toBeVisible();
});
