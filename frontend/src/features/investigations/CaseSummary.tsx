import { StatusBadge } from '@/components/ui/StatusBadge';
import type { Investigation } from '@/types/api';
import { formatDateTime } from '@/utils/format';

interface CaseSummaryProps {
  investigation: Investigation;
  machineCode: string;
}

export function CaseSummary({ investigation, machineCode }: CaseSummaryProps) {
  return (
    <section className="panel p-4" aria-label="Case summary">
      <div className="flex flex-wrap items-center gap-2">
        <StatusBadge status={investigation.status} />
        <span className="text-xs text-ink-muted">Case {investigation.id}</span>
        <span className="text-xs text-ink-faint">
          Opened {formatDateTime(investigation.created_at)}
        </span>
        {investigation.closed_at && (
          <span className="text-xs text-ink-faint">
            Closed {formatDateTime(investigation.closed_at)}
          </span>
        )}
      </div>
      <dl className="mt-3 grid grid-cols-1 gap-x-6 gap-y-2 text-sm sm:grid-cols-3">
        <div>
          <dt className="text-xs text-ink-muted">Scope</dt>
          <dd className="font-mono">{machineCode}</dd>
        </div>
        <div>
          <dt className="text-xs text-ink-muted">Window start</dt>
          <dd>{formatDateTime(investigation.window_start)}</dd>
        </div>
        <div>
          <dt className="text-xs text-ink-muted">Window end</dt>
          <dd>{formatDateTime(investigation.window_end)}</dd>
        </div>
      </dl>
      <h2 className="mt-4 text-xs font-semibold tracking-wide text-ink-muted uppercase">
        Findings
      </h2>
      <p className="mt-1 text-sm leading-relaxed text-ink">
        {investigation.summary ?? 'No summary was produced.'}
      </p>
      {investigation.conclusion && (
        <>
          <h2 className="mt-4 text-xs font-semibold tracking-wide text-ink-muted uppercase">
            Engineer conclusion
          </h2>
          <p className="mt-1 text-sm leading-relaxed whitespace-pre-wrap text-ink">
            {investigation.conclusion}
          </p>
        </>
      )}
    </section>
  );
}
