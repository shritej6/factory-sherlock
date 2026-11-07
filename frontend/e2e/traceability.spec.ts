import { expect, test } from '@playwright/test';
import type { APIRequestContext, Locator, Page } from '@playwright/test';

import { apiGet, apiToken, signIn } from './support/auth';

/** Steel bar stock lot consumed by CNC-03 batches in the demo scenario. */
const TRACED_LOT = 'L201';
/** The investigation test flags CNC-03 batches, so the quarantine test leaves CNC-03 lots alone. */
const PROTECTED_MACHINE = 'CNC-03';
const LINEAGE_TABLE = "Material lots used by the unit's batch";

interface MaterialLot {
  id: number;
  lot_number: string;
  status: string;
}

interface ForwardTrace {
  batches: { batch_number: string; machine_code: string }[];
}

/** Fails with a data message instead of a UI timeout when the lot is missing from the seed. */
async function assertLotExists(request: APIRequestContext, lotNumber: string): Promise<void> {
  const token = await apiToken(request, 'engineer');
  const lots = await apiGet<MaterialLot[]>(request, token, '/material-lots');
  if (!lots.some((lot) => lot.lot_number === lotNumber)) {
    throw new Error(
      `Material lot ${lotNumber} is not in the database. ` +
        'Seed the demo scenario (see frontend/e2e/README.md) and run again.',
    );
  }
}

async function traceLot(
  page: Page,
  request: APIRequestContext,
  lotNumber: string,
): Promise<Locator> {
  await assertLotExists(request, lotNumber);
  const form = page.getByRole('form', { name: 'Trace lot' });
  await form.getByLabel('Lot number').fill(lotNumber);
  await form.getByRole('button', { name: 'Trace lot' }).click();
  const table = page.getByRole('table', { name: `Batches that consumed lot ${lotNumber}` });
  await expect(table).toBeVisible();
  return table;
}

async function traceUnit(page: Page, serialNumber: string): Promise<void> {
  const form = page.getByRole('form', { name: 'Trace unit' });
  await form.getByLabel('Serial number').fill(serialNumber);
  await form.getByRole('button', { name: 'Trace unit' }).click();
  await expect(page.getByRole('table', { name: LINEAGE_TABLE })).toBeVisible();
}

/** Body rows of a DataTable (the header row has no cells, only column headers). */
function bodyRows(table: Locator): Locator {
  return table.getByRole('row').filter({ has: table.page().getByRole('cell') });
}

async function columnIndex(table: Locator, header: string): Promise<number> {
  const headers = await table.getByRole('columnheader').allTextContents();
  const index = headers.indexOf(header);
  expect(index, `column "${header}" in ${headers.join(', ')}`).toBeGreaterThanOrEqual(0);
  return index;
}

/**
 * Picks an AVAILABLE lot whose batches all ran on machines other than CNC-03, so
 * quarantining it does not change the evidence of the investigation test. Each run
 * consumes one such lot; the demo scenario provides six (L301 to L303, L401 to L403).
 */
async function pickQuarantineCandidate(
  request: APIRequestContext,
): Promise<{ lot: MaterialLot; serial: string }> {
  const token = await apiToken(request, 'engineer');
  const lots = await apiGet<MaterialLot[]>(request, token, '/material-lots');
  const available = lots
    .filter((lot) => lot.status === 'AVAILABLE')
    .sort((a, b) => a.lot_number.localeCompare(b.lot_number));
  for (const lot of available) {
    const trace = await apiGet<ForwardTrace>(
      request,
      token,
      `/traceability/forward/${lot.lot_number}`,
    );
    const batches = trace.batches;
    if (batches.length === 0) continue;
    if (batches.some((batch) => batch.machine_code === PROTECTED_MACHINE)) continue;
    return { lot, serial: `${batches[0].batch_number}-U0001` };
  }
  throw new Error(
    `No AVAILABLE lot outside ${PROTECTED_MACHINE} is left to quarantine. ` +
      'Reset the demo data (see frontend/e2e/README.md) and run again.',
  );
}

test.describe('traceability', () => {
  test(`forward trace of lot ${TRACED_LOT} lists its batches with unit counts`, async ({
    page,
    request,
  }) => {
    await signIn(page, 'engineer');
    await page.goto('/traceability');

    const table = await traceLot(page, request, TRACED_LOT);
    const rows = bodyRows(table);
    await expect(rows.first()).toBeVisible();
    expect(await rows.count()).toBeGreaterThan(0);

    const batchColumn = await columnIndex(table, 'Batch');
    const unitsColumn = await columnIndex(table, 'Units');
    for (const row of await rows.all()) {
      const cells = row.getByRole('cell');
      await expect(cells.nth(batchColumn)).not.toBeEmpty();
      await expect(cells.nth(unitsColumn)).toHaveText(/^[1-9][\d,]*$/);
    }
  });

  test(`backward trace of a unit from lot ${TRACED_LOT} shows its lot and inspections`, async ({
    page,
    request,
  }) => {
    await signIn(page, 'engineer');
    await page.goto('/traceability');

    const table = await traceLot(page, request, TRACED_LOT);
    const batchColumn = await columnIndex(table, 'Batch');
    const batchNumber = await bodyRows(table)
      .first()
      .getByRole('cell')
      .nth(batchColumn)
      .innerText();
    const serial = `${batchNumber}-U0001`;

    await traceUnit(page, serial);
    await expect(page.getByText(serial, { exact: true })).toBeVisible();
    await expect(page.getByText(batchNumber, { exact: true }).last()).toBeVisible();
    const inspectionSummary = page.locator('dt:has-text("Inspection summary") + dd');
    await expect(inspectionSummary).not.toHaveText('Not inspected');
    await expect(inspectionSummary).toHaveText(/=/);

    const lineage = page.getByRole('table', { name: LINEAGE_TABLE });
    await expect(lineage.getByRole('row').filter({ hasText: TRACED_LOT })).toHaveCount(1);
  });

  test('an engineer quarantines an available lot and its status chip updates', async ({
    page,
    request,
  }) => {
    const { lot, serial } = await pickQuarantineCandidate(request);

    await signIn(page, 'engineer');
    await page.goto('/traceability');
    await traceUnit(page, serial);
    const lotRow = page
      .getByRole('table', { name: LINEAGE_TABLE })
      .getByRole('row')
      .filter({ hasText: lot.lot_number });
    await expect(lotRow.getByText('Available', { exact: true })).toBeVisible();

    const form = page.getByRole('form', { name: 'Quarantine material lot' });
    await form.getByLabel('Material lot').selectOption(String(lot.id));
    await form.getByLabel('Reason').fill(`Browser test: supplier notice for ${lot.lot_number}`);
    await form.getByRole('button', { name: 'Quarantine lot and its batches' }).click();

    await expect(form.getByText(`Lot ${lot.lot_number} is quarantined;`)).toBeVisible();
    // The form only offers lots that are not quarantined, so the lot disappears from it.
    await expect(form.getByLabel('Material lot').locator(`option[value="${lot.id}"]`)).toHaveCount(
      0,
    );

    // Trace results are cached for 15 seconds; a fresh page load reads the stored status.
    await page.reload();
    await traceUnit(page, serial);
    await expect(lotRow.getByText('Quarantined', { exact: true })).toBeVisible();
  });
});
