import { expect, test } from '@playwright/test';

import { API, apiGet, apiToken, bearer, signIn } from './support/auth';

interface Product {
  id: number;
}

test.describe('roles', () => {
  test('a viewer sees the orders table without create, edit, or status controls', async ({
    page,
  }) => {
    await signIn(page, 'viewer');
    await page.goto('/orders');

    await expect(page.getByRole('heading', { name: 'Production Orders' })).toBeVisible();
    const table = page.getByRole('table', { name: 'Production orders' });
    await expect(table).toBeVisible();
    await expect(table.getByText('Read only').first()).toBeVisible();

    await expect(page.getByRole('button', { name: 'New order' })).toHaveCount(0);
    await expect(page.getByRole('group', { name: /^Transitions for / })).toHaveCount(0);
    await expect(page.getByRole('button', { name: /^Edit / })).toHaveCount(0);
    await expect(table.getByRole('button')).toHaveCount(0);
  });

  test('a direct order creation with the viewer token is refused with 403', async ({ request }) => {
    const token = await apiToken(request, 'viewer');
    const products = await apiGet<Product[]>(request, token, '/products');
    expect(products.length).toBeGreaterThan(0);

    const response = await request.post(`${API}/production-orders`, {
      headers: bearer(token),
      data: {
        order_number: `E2E-VIEWER-${Date.now()}`,
        product_id: products[0].id,
        machine_id: null,
        quantity_planned: 10,
        due_date: null,
      },
    });

    expect(response.status()).toBe(403);
    const body = (await response.json()) as { error: string; message: string };
    expect(body.error).toBe('AuthorizationError');
    expect(body.message).not.toContain('SELECT');
  });
});
