import { ApiError } from '@/services/http';

interface FieldError {
  field: string;
  message: string;
}

/** Produces the sentence shown to the user for any failure. */
export function describeError(error: unknown): string {
  if (error instanceof ApiError) {
    const fieldErrors = extractFieldErrors(error);
    if (fieldErrors.length > 0) {
      return `${error.message}: ${fieldErrors.map((e) => `${e.field || 'body'} ${e.message}`).join('; ')}`;
    }
    return error.message;
  }
  if (error instanceof Error) return error.message;
  return 'An unexpected error occurred.';
}

export function extractFieldErrors(error: ApiError): FieldError[] {
  const raw = error.details.errors;
  if (!Array.isArray(raw)) return [];
  return raw.filter(isFieldError);
}

function isFieldError(value: unknown): value is FieldError {
  if (typeof value !== 'object' || value === null) return false;
  const candidate = value as Record<string, unknown>;
  return typeof candidate.field === 'string' && typeof candidate.message === 'string';
}

export function isNotFound(error: unknown): boolean {
  return error instanceof ApiError && error.status === 404;
}
