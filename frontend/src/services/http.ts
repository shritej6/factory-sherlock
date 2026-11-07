import type { ErrorResponse } from '@/types/api';

export const API_PREFIX = '/api/v1';
const TOKEN_KEY = 'factory-sherlock.token';
export const UNAUTHORIZED_EVENT = 'factory-sherlock:unauthorized';

/** The backend envelope; details and request_id are tolerated as missing for non-API failures. */
export type ErrorBody = Pick<ErrorResponse, 'error' | 'message'> & Partial<ErrorResponse>;

export class ApiError extends Error {
  readonly status: number;
  readonly error: string;
  readonly details: Record<string, unknown>;
  /** Correlation id logged by the backend; quote it when reporting a failure. */
  readonly requestId: string | null;

  constructor(status: number, body: ErrorBody) {
    super(body.message);
    this.name = 'ApiError';
    this.status = status;
    this.error = body.error;
    this.details = body.details ?? {};
    this.requestId = body.request_id ?? null;
  }
}

let storageWarned = false;

/** Storage can be unavailable in private windows; the session then lasts one page load. */
function warnStorageUnavailable(cause: unknown): void {
  if (storageWarned) return;
  storageWarned = true;
  console.warn('Token storage is unavailable; the session will not survive a reload.', cause);
}

export const tokenStore = {
  get(): string | null {
    try {
      return window.localStorage.getItem(TOKEN_KEY);
    } catch (cause) {
      warnStorageUnavailable(cause);
      return null;
    }
  },
  set(token: string): void {
    try {
      window.localStorage.setItem(TOKEN_KEY, token);
    } catch (cause) {
      warnStorageUnavailable(cause);
    }
  },
  clear(): void {
    try {
      window.localStorage.removeItem(TOKEN_KEY);
    } catch (cause) {
      warnStorageUnavailable(cause);
    }
  },
};

export type QueryValue = string | number | boolean | null | undefined;

export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE';
  /** A FormData body is sent as multipart and the browser sets its own boundary header. */
  body?: unknown;
  query?: Record<string, QueryValue>;
  auth?: boolean;
}

export function buildQuery(query: Record<string, QueryValue> | undefined): string {
  if (!query) return '';
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null || value === '') continue;
    params.set(key, String(value));
  }
  const text = params.toString();
  return text ? `?${text}` : '';
}

/** Normalises any error shape coming back from fetch into an ApiError. */
export async function toApiError(response: Response): Promise<ApiError> {
  let body: ErrorBody = {
    error: 'HttpError',
    message: `Request failed with status ${response.status}`,
  };
  try {
    const parsed: unknown = await response.json();
    if (isErrorResponse(parsed)) body = parsed;
  } catch {
    // Non-JSON error bodies keep the generic message built above.
  }
  return new ApiError(response.status, body);
}

function isErrorResponse(value: unknown): value is ErrorBody {
  if (typeof value !== 'object' || value === null) return false;
  const candidate = value as Record<string, unknown>;
  return typeof candidate.error === 'string' && typeof candidate.message === 'string';
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, query, auth = true } = options;
  const headers: Record<string, string> = { Accept: 'application/json' };
  const isForm = body instanceof FormData;
  if (body !== undefined && !isForm) headers['Content-Type'] = 'application/json';
  const token = auth ? tokenStore.get() : null;
  if (token) headers.Authorization = `Bearer ${token}`;

  let response: Response;
  try {
    response = await fetch(`${API_PREFIX}${path}${buildQuery(query)}`, {
      method,
      headers,
      body: body === undefined ? undefined : isForm ? body : JSON.stringify(body),
    });
  } catch (cause) {
    throw new ApiError(0, {
      error: 'NetworkError',
      message: 'The server could not be reached. Check that the backend is running.',
      details: { cause: cause instanceof Error ? cause.message : String(cause) },
    });
  }

  if (!response.ok) {
    const error = await toApiError(response);
    if (error.status === 401 && auth) {
      tokenStore.clear();
      window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
    }
    throw error;
  }
  if (response.status === 204) return undefined as T;
  try {
    return (await response.json()) as T;
  } catch (cause) {
    throw new ApiError(response.status, {
      error: 'BadResponse',
      message: 'The server returned a response that could not be read.',
      details: { cause: cause instanceof Error ? cause.message : String(cause) },
    });
  }
}
