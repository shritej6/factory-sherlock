import { defineConfig, devices } from '@playwright/test';

import { demoPassword } from './e2e/support/env';

const isCI = Boolean(process.env.CI);
const baseURL = process.env.E2E_BASE_URL ?? 'http://localhost:5183';
const frontendPort = new URL(baseURL).port || '5183';
const apiPort = process.env.E2E_API_PORT ?? '8013';
// CI runs the Chromium that "playwright install chromium" downloads. Locally,
// E2E_BROWSER_CHANNEL=chrome uses the installed Google Chrome when that
// download is blocked.
const channel = isCI ? undefined : process.env.E2E_BROWSER_CHANNEL;

// Resolve the demo password once so a missing value fails before any server starts.
process.env.E2E_PASSWORD = demoPassword();

export default defineConfig({
  testDir: 'e2e',
  forbidOnly: isCI,
  retries: isCI ? 1 : 0,
  reporter: [['list'], ['html', { outputFolder: 'playwright-report', open: 'never' }]],
  expect: { timeout: 10_000 },
  use: {
    baseURL,
    // Traces help with a flaky retry but are uploaded with the CI report, so the spec
    // sources stay out of them. The login spec switches tracing off entirely because it
    // types the demo password; the shared signIn helper never puts it in the browser.
    trace: { mode: 'on-first-retry', sources: false },
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'], ...(channel ? { channel } : {}) },
    },
  ],
  webServer: [
    {
      command: `uv run uvicorn app.main:app --host 127.0.0.1 --port ${apiPort} --no-proxy-headers`,
      cwd: '../backend',
      url: `http://127.0.0.1:${apiPort}/api/v1/health`,
      reuseExistingServer: !isCI,
      timeout: 120_000,
    },
    {
      command: `pnpm dev --port ${frontendPort} --strictPort`,
      url: baseURL,
      reuseExistingServer: !isCI,
      timeout: 120_000,
      env: { VITE_API_PROXY_TARGET: `http://127.0.0.1:${apiPort}` },
    },
  ],
});
