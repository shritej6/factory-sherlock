import { useSearchParams } from 'react-router';

import { PageHeader } from '@/components/ui/PageHeader';
import { Panel } from '@/components/ui/Panel';
import { StatTile } from '@/components/ui/StatTile';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { EmptyState, ErrorState, LoadingState } from '@/components/ui/States';
import { useMachineEvents, useMachines, useQualitySummary } from '@/hooks/queries';
import { useAuth } from '@/hooks/useAuth';
import { formatDateTime, formatNumber, formatPercent } from '@/utils/format';

import { EventTimeline } from './EventTimeline';
import { MachineStatusForm } from './MachineStatusForm';

export function MachinesPage() {
  const { can } = useAuth();
  const machines = useMachines();
  const [params, setParams] = useSearchParams();
  const requested = Number(params.get('machine'));
  const selectedId = machines.data?.some((m) => m.id === requested)
    ? requested
    : (machines.data?.[0]?.id ?? null);
  const selected = machines.data?.find((m) => m.id === selectedId) ?? null;
  const events = useMachineEvents(selectedId);
  const summary = useQualitySummary(selectedId ? { machine_id: selectedId } : {});

  return (
    <>
      <PageHeader
        title="Machine Monitoring"
        description="Select a machine to see its event timeline and quality figures."
      />
      {machines.isPending && <LoadingState label="Loading machines" />}
      {machines.isError && (
        <ErrorState error={machines.error} onRetry={() => void machines.refetch()} />
      )}
      {machines.data && machines.data.length === 0 && <EmptyState title="No machines registered" />}
      {machines.data && machines.data.length > 0 && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-[280px_1fr]">
          <Panel title="Machines" className="self-start">
            <ul className="flex flex-col gap-1" aria-label="Machine list">
              {machines.data.map((machine) => (
                <li key={machine.id}>
                  <button
                    type="button"
                    aria-current={machine.id === selectedId ? 'true' : undefined}
                    onClick={() => setParams({ machine: String(machine.id) })}
                    className={`flex w-full items-center justify-between gap-2 rounded-panel border px-3 py-2 text-left text-sm ${machine.id === selectedId ? 'border-accent bg-accent-soft' : 'border-transparent hover:bg-surface-muted'}`}
                  >
                    <span>
                      <span className="block font-mono font-semibold text-ink">{machine.code}</span>
                      <span className="block text-xs text-ink-muted">{machine.name}</span>
                    </span>
                    <StatusBadge status={machine.status} />
                  </button>
                </li>
              ))}
            </ul>
          </Panel>
          {selected && (
            <div className="flex min-w-0 flex-col gap-4">
              <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                <StatTile
                  label="Status"
                  value={selected.status.replace('_', ' ')}
                  detail={`Updated ${formatDateTime(selected.updated_at)}`}
                />
                <StatTile
                  label="Inspected"
                  value={summary.data ? formatNumber(summary.data.total_inspected) : '...'}
                />
                <StatTile
                  label="Failed"
                  value={summary.data ? formatNumber(summary.data.failed) : '...'}
                />
                <StatTile
                  label="Defect rate"
                  value={summary.data ? formatPercent(summary.data.defect_rate) : '...'}
                />
              </div>
              {summary.isError && (
                <ErrorState error={summary.error} onRetry={() => void summary.refetch()} />
              )}
              <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1fr_320px]">
                <Panel title="Event timeline" description={`${selected.code} · most recent first`}>
                  {events.isPending && <LoadingState label="Loading events" />}
                  {events.isError && (
                    <ErrorState error={events.error} onRetry={() => void events.refetch()} />
                  )}
                  {events.data && <EventTimeline events={events.data} />}
                </Panel>
                <Panel title="Change status" className="self-start">
                  {can('machine.changeStatus') ? (
                    <MachineStatusForm
                      key={`${selected.id}-${selected.status}`}
                      machine={selected}
                    />
                  ) : (
                    <p className="text-sm text-ink-muted">
                      Your role can view machine states but not change them.
                    </p>
                  )}
                </Panel>
              </div>
            </div>
          )}
        </div>
      )}
    </>
  );
}
