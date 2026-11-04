import { Link } from 'react-router';

import type { Column } from '@/components/ui/DataTable';
import { DataTable } from '@/components/ui/DataTable';
import { Disclosure } from '@/components/ui/Disclosure';
import { PageHeader } from '@/components/ui/PageHeader';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { ErrorState, LoadingState } from '@/components/ui/States';
import { useInvestigations, useMachines } from '@/hooks/queries';
import { useAuth } from '@/hooks/useAuth';
import type { Investigation } from '@/types/api';
import { formatDateTime, formatNumber } from '@/utils/format';

import { OpenInvestigationForm } from './OpenInvestigationForm';

export function InvestigationsPage() {
  const { can } = useAuth();
  const investigations = useInvestigations();
  const machines = useMachines();
  const machineCode = (id: number | null) =>
    id === null ? 'Fleet' : (machines.data?.find((m) => m.id === id)?.code ?? `#${id}`);

  const columns: Column<Investigation>[] = [
    {
      key: 'title',
      header: 'Case',
      render: (i) => (
        <Link to={`/investigations/${i.id}`} className="font-medium text-accent hover:underline">
          {i.title}
        </Link>
      ),
    },
    { key: 'status', header: 'Status', render: (i) => <StatusBadge status={i.status} /> },
    {
      key: 'machine',
      header: 'Scope',
      render: (i) => <span className="font-mono">{machineCode(i.machine_id)}</span>,
    },
    {
      key: 'window',
      header: 'Window',
      render: (i) => `${formatDateTime(i.window_start)} to ${formatDateTime(i.window_end)}`,
    },
    {
      key: 'evidence',
      header: 'Evidence',
      align: 'right',
      render: (i) => formatNumber(i.evidence.length),
    },
    {
      key: 'batches',
      header: 'Flagged batches',
      align: 'right',
      render: (i) => formatNumber(i.batch_links.length),
    },
    { key: 'created_at', header: 'Opened', render: (i) => formatDateTime(i.created_at) },
  ];

  return (
    <>
      <PageHeader
        title="Investigations"
        description="Each case runs six rules against the database and keeps the SQL and rows as evidence."
        actions={
          can('investigation.manage') && (
            <Disclosure label="Open investigation">
              {(close) => <OpenInvestigationForm onDone={close} />}
            </Disclosure>
          )
        }
      />
      <div className="panel">
        {investigations.isPending && <LoadingState label="Loading investigations" />}
        {investigations.isError && (
          <div className="p-4">
            <ErrorState
              error={investigations.error}
              onRetry={() => void investigations.refetch()}
            />
          </div>
        )}
        {investigations.data && (
          <DataTable
            columns={columns}
            rows={investigations.data}
            rowKey={(i) => i.id}
            caption="Investigations"
            emptyTitle="No investigations have been opened"
            emptyHint={
              can('investigation.manage')
                ? 'Open one to run the rules against a machine and time window.'
                : 'An engineer can open one from this screen.'
            }
          />
        )}
      </div>
    </>
  );
}
