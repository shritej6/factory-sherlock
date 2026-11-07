import { Link, useParams } from 'react-router';

import { PageHeader } from '@/components/ui/PageHeader';
import { Panel } from '@/components/ui/Panel';
import { EmptyState, ErrorState, LoadingState } from '@/components/ui/States';
import { LOOKUP_PAGE, useBatches, useInvestigation, useMachines } from '@/hooks/queries';
import { useAuth } from '@/hooks/useAuth';
import type { Investigation } from '@/types/api';

import { CaseSummary } from './CaseSummary';
import { EvidenceCard } from './EvidenceCard';
import { FlaggedBatches } from './FlaggedBatches';
import { StatusActions } from './StatusActions';

function batchRatesFromEvidence(investigation: Investigation): Map<number, number> {
  const rates = new Map<number, number>();
  const r5 = investigation.evidence.find((e) => e.rule_code === 'R5');
  for (const row of r5?.result_rows ?? []) {
    if (typeof row.batch_id === 'number' && typeof row.defect_rate === 'number')
      rates.set(row.batch_id, row.defect_rate);
  }
  return rates;
}

export function InvestigationDetailPage() {
  const { id } = useParams();
  const investigationId = Number(id);
  const { can } = useAuth();
  const investigation = useInvestigation(investigationId);
  const machines = useMachines();
  const batches = useBatches({
    ...(investigation.data?.machine_id ? { machine_id: investigation.data.machine_id } : {}),
    ...LOOKUP_PAGE,
  });

  if (!Number.isInteger(investigationId) || investigationId <= 0) {
    return (
      <ErrorState
        error={new Error('The investigation id in the address is not valid.')}
        title="Invalid case"
      />
    );
  }
  if (investigation.isPending) return <LoadingState label="Loading case" />;
  if (investigation.isError)
    return (
      <ErrorState
        error={investigation.error}
        onRetry={() => void investigation.refetch()}
        title="Could not load the case"
      />
    );

  const data = investigation.data;
  const machineCode =
    data.machine_id === null
      ? 'Fleet'
      : (machines.data?.find((m) => m.id === data.machine_id)?.code ??
        `Machine ${data.machine_id}`);
  const evidence = [...data.evidence].sort((a, b) => a.sequence - b.sequence);

  return (
    <>
      <PageHeader
        title={data.title}
        description="Case board. Each evidence card shows what a rule found, the rows behind it, and the exact SQL it ran."
        actions={
          <Link to="/investigations" className="text-sm text-accent hover:underline">
            All investigations
          </Link>
        }
      />
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1fr_340px]">
        <div className="flex min-w-0 flex-col gap-4">
          <CaseSummary investigation={data} machineCode={machineCode} />
          <section aria-label="Evidence" className="flex flex-col gap-4">
            <h2 className="text-xs font-semibold tracking-wide text-ink-muted uppercase">
              Evidence ({evidence.length} rules)
            </h2>
            {evidence.length === 0 && (
              <EmptyState title="No rule produced evidence for this window" />
            )}
            {evidence.map((card) => (
              <EvidenceCard key={card.id} evidence={card} />
            ))}
          </section>
        </div>
        <div className="flex flex-col gap-4 xl:sticky xl:top-5 xl:self-start">
          <Panel title="Case status">
            {can('investigation.manage') ? (
              <StatusActions key={data.status} investigation={data} />
            ) : (
              <p className="text-sm text-ink-muted">
                Engineers and administrators can change the case status.
              </p>
            )}
          </Panel>
          <Panel
            title="Flagged batches"
            description="Batches whose defect rate exceeded the review threshold."
          >
            <FlaggedBatches
              links={data.batch_links}
              batches={batches.data?.items}
              rates={batchRatesFromEvidence(data)}
              canQuarantine={can('batch.quarantine')}
            />
          </Panel>
        </div>
      </div>
    </>
  );
}
