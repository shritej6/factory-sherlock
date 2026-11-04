import { ResultRowsTable } from '@/components/ui/DataTable';
import { SqlDisclosure } from '@/components/ui/SqlDisclosure';
import type { Evidence } from '@/types/api';
import { formatNumber } from '@/utils/format';

export function EvidenceCard({ evidence }: { evidence: Evidence }) {
  return (
    <article
      className="panel p-4"
      aria-labelledby={`evidence-${evidence.id}-title`}
      data-testid="evidence-card"
    >
      <header className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="rounded-sm bg-accent-soft px-1.5 py-0.5 font-mono text-xs font-semibold text-accent">
          {evidence.rule_code}
        </span>
        <h3 id={`evidence-${evidence.id}-title`} className="text-sm font-semibold text-ink">
          {evidence.title}
        </h3>
        <span className="ml-auto text-xs text-ink-faint">
          {formatNumber(evidence.result_rows.length)} row(s)
        </span>
      </header>
      <p className="mt-2 text-sm leading-relaxed text-ink">{evidence.narrative}</p>
      <div className="mt-3">
        <ResultRowsTable
          rows={evidence.result_rows}
          caption={`${evidence.rule_code} result rows`}
          emptyTitle="This rule returned no rows"
        />
      </div>
      <SqlDisclosure sql={evidence.query_sql} queryName={evidence.query_name} />
    </article>
  );
}
