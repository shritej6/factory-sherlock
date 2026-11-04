import { describe, expect, it, vi } from 'vitest';

import { describeError } from '@/utils/errors';
import { jsonResponse, mockFetch } from '@tests/helpers';

import { ApiError, buildQuery, request, tokenStore, UNAUTHORIZED_EVENT } from './http';

describe('request error mapping', () => {
  it('maps the backend error envelope to an ApiError with field details', async () => {
    mockFetch([
      [
        /\/production-orders$/,
        () =>
          jsonResponse(
            {
              error: 'ValidationError',
              message: 'Request failed validation',
              details: {
                errors: [{ field: 'quantity_planned', message: 'Input should be greater than 0' }],
              },
            },
            422,
          ),
      ],
    ]);
    const failure = await request('/production-orders', { method: 'POST', body: {} }).catch(
      (e: unknown) => e,
    );
    expect(failure).toBeInstanceOf(ApiError);
    const error = failure as ApiError;
    expect(error.status).toBe(422);
    expect(error.error).toBe('ValidationError');
    expect(describeError(error)).toBe(
      'Request failed validation: quantity_planned Input should be greater than 0',
    );
  });

  it('falls back to a status message when the body is not the error envelope', async () => {
    mockFetch([[/\/machines$/, () => new Response('<html>Bad gateway</html>', { status: 502 })]]);
    const error = (await request('/machines').catch((e: unknown) => e)) as ApiError;
    expect(error.status).toBe(502);
    expect(error.error).toBe('HttpError');
    expect(error.message).toBe('Request failed with status 502');
  });

  it('turns a network failure into a NetworkError the UI can show', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        throw new TypeError('Failed to fetch');
      }),
    );
    const error = (await request('/machines').catch((e: unknown) => e)) as ApiError;
    expect(error.status).toBe(0);
    expect(error.error).toBe('NetworkError');
    expect(describeError(error)).toMatch(/could not be reached/);
  });

  it('clears the token and announces an unauthorized response', async () => {
    tokenStore.set('stale');
    const listener = vi.fn();
    window.addEventListener(UNAUTHORIZED_EVENT, listener);
    mockFetch([
      [
        /\/auth\/me$/,
        () =>
          jsonResponse(
            { error: 'AuthenticationError', message: 'Access token is invalid', details: {} },
            401,
          ),
      ],
    ]);
    await expect(request('/auth/me')).rejects.toBeInstanceOf(ApiError);
    expect(tokenStore.get()).toBeNull();
    expect(listener).toHaveBeenCalledTimes(1);
    window.removeEventListener(UNAUTHORIZED_EVENT, listener);
  });

  it('maps a 2xx response with a non-JSON body to a BadResponse error', async () => {
    mockFetch([[/\/machines$/, () => new Response('<html>proxy page</html>', { status: 200 })]]);
    const error = (await request('/machines').catch((e: unknown) => e)) as ApiError;
    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(200);
    expect(error.error).toBe('BadResponse');
  });

  it('omits empty query parameters', () => {
    expect(buildQuery({ status: '', machine_id: 3, limit: undefined, hours: null })).toBe(
      '?machine_id=3',
    );
    expect(buildQuery({})).toBe('');
  });
});
