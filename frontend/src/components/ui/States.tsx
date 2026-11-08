import type { ReactNode } from 'react';

import { ApiError } from '@/services/http';
import { describeError } from '@/utils/errors';

import { Button } from './Button';

export function LoadingState({ label = 'Loading' }: { label?: string }) {
  return (
    <div role="status" aria-live="polite" className="px-2 py-6 text-center text-sm text-ink-muted">
      {label}
    </div>
  );
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="border border-dashed border-border-strong px-4 py-8 text-center">
      <p className="text-sm font-medium text-ink">{title}</p>
      {hint && <p className="mt-1 text-xs text-ink-muted">{hint}</p>}
    </div>
  );
}

/** The backend correlation id, shown with every failure so it can be quoted in a report. */
function RequestId({ error }: { error: unknown }) {
  if (!(error instanceof ApiError) || !error.requestId) return null;
  return <p className="mt-1 font-mono text-xs text-ink-muted">Request id {error.requestId}</p>;
}

export function ErrorState({
  error,
  onRetry,
  title = 'Something went wrong',
}: {
  error: unknown;
  onRetry?: () => void;
  title?: string;
}) {
  return (
    <div
      role="alert"
      className="border border-l-4 border-status-fault bg-status-fault-soft px-4 py-3 text-sm text-ink"
    >
      <p className="font-medium">{title}</p>
      <p className="mt-1 text-ink-muted">{describeError(error)}</p>
      <RequestId error={error} />
      {onRetry && (
        <Button size="sm" className="mt-3" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}

export function InlineNotice({
  tone,
  children,
}: {
  tone: 'error' | 'success' | 'info';
  children: ReactNode;
}) {
  const classes = {
    error: 'border-status-fault bg-status-fault-soft',
    success: 'border-status-running bg-status-running-soft',
    info: 'border-status-info bg-status-info-soft',
  }[tone];
  return (
    <div
      role={tone === 'error' ? 'alert' : 'status'}
      className={`border border-l-4 px-3 py-2 text-sm text-ink ${classes}`}
    >
      {children}
    </div>
  );
}

/**
 * Failure notice for a form or row action. Shows the backend message (or the text passed as
 * children) and the request id, so mutation failures read the same as ErrorState.
 */
export function ErrorNotice({ error, children }: { error: unknown; children?: ReactNode }) {
  return (
    <InlineNotice tone="error">
      <p>{children ?? describeError(error)}</p>
      <RequestId error={error} />
    </InlineNotice>
  );
}
