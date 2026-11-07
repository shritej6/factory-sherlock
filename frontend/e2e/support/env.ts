import { existsSync, readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

// frontend/e2e/support -> repository root
const REPO_ENV_FILE = fileURLToPath(new URL('../../../.env', import.meta.url));

/** Reads one KEY=value line from the repository .env without loading anything else. */
function readEnvValue(key: string): string | null {
  if (!existsSync(REPO_ENV_FILE)) return null;
  for (const line of readFileSync(REPO_ENV_FILE, 'utf8').split('\n')) {
    if (!line.startsWith(`${key}=`)) continue;
    const value = line.slice(key.length + 1).trim();
    return value.replace(/^(['"])(.*)\1$/, '$2') || null;
  }
  return null;
}

/**
 * The password of the seeded demo accounts: E2E_PASSWORD when set (CI), otherwise
 * SEED_DEMO_PASSWORD from the repository .env (local runs). Never written to the report.
 */
export function demoPassword(): string {
  const value = process.env.E2E_PASSWORD || readEnvValue('SEED_DEMO_PASSWORD');
  if (!value) {
    throw new Error(
      'Set E2E_PASSWORD, or SEED_DEMO_PASSWORD in the repository .env, before running the end-to-end suite.',
    );
  }
  return value;
}
