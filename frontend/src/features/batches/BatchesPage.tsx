import { useMemo, useState } from 'react';
import { useSearchParams } from 'react-router';

import type { Column } from '@/components/ui/DataTable';
import { DataTable } from '@/components/ui/DataTable';
import { Disclosure } from '@/components/ui/Disclosure';
import { SelectField } from '@/components/ui/Field';
import { PageHeader } from '@/components/ui/PageHeader';
import { PageBody, Pagination } from '@/components/ui/Pagination';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { ErrorNotice, ErrorState, InlineNotice, LoadingState } from '@/components/ui/States';
import { LOOKUP_PAGE, useBatches, useMachines, useMaterialLots, useOrders } from '@/hooks/queries';
import { useAuth } from '@/hooks/useAuth';
import { usePageState } from '@/hooks/usePageState';
import type { BatchStatus, ProductionBatch } from '@/types/api';
import { BATCH_STATUSES } from '@/types/constants';
import { formatDateTime, formatNumber, titleCase } from '@/utils/format';

import { BatchActions } from './BatchActions';
import { BatchForm } from './BatchForm';

export function BatchesPage() {
  const { can } = useAuth();
  const [searchParams] = useSearchParams();
  const highlightedId = Number(searchParams.get('batch')) || null;
  const [orderId, setOrderId] = useState('');
  const [machineId, setMachineId] = useState(searchParams.get('machine') ?? '');
  const [status, setStatus] = useState<BatchStatus | ''>('');
  const [actionError, setActionError] = useState<unknown>(null);
  const filters = {
    ...(orderId ? { order_id: Number(orderId) } : {}),
    ...(machineId ? { machine_id: Number(machineId) } : {}),
    ...(status ? { status } : {}),
  };
  const { page, setPage, resetOffset } = usePageState();
  const batches = useBatches({ ...filters, ...page });
  const orders = useOrders(LOOKUP_PAGE);
  const machines = useMachines();
  const lots = useMaterialLots();

  const machineCodes = useMemo(
    () => new Map(machines.data?.map((m) => [m.id, m.code])),
    [machines.data],
  );
  const lotNumbers = useMemo(
    () => new Map(lots.data?.map((l) => [l.id, l.lot_number])),
    [lots.data],
  );
  const machineCode = (id: number) => machineCodes.get(id) ?? `#${id}`;
  const lotNumber = (id: number) => lotNumbers.get(id) ?? `#${id}`;

  const columns: Column<ProductionBatch>[] = [
    {
      key: 'batch_number',
      header: 'Batch',
      render: (b) => (
        <span
          className={`font-mono font-medium ${b.id === highlightedId ? 'rounded-sm bg-accent-soft px-1 text-accent' : ''}`}
        >
          {b.batch_number}
        </span>
      ),
    },
    {
      key: 'order',
      header: 'Order',
      render: (b) => <span className="font-mono">{b.order_number}</span>,
    },
    {
      key: 'machine',
      header: 'Machine',
      render: (b) => <span className="font-mono">{machineCode(b.machine_id)}</span>,
    },
    { key: 'status', header: 'Status', render: (b) => <StatusBadge status={b.status} /> },
    { key: 'quantity', header: 'Units', align: 'right', render: (b) => formatNumber(b.quantity) },
    { key: 'started_at', header: 'Started', render: (b) => formatDateTime(b.started_at) },
    {
      key: 'completed_at',
      header: 'Completed',
      render: (b) => formatDateTime(b.completed_at) || '',
    },
    {
      key: 'materials',
      header: 'Material lots',
      render: (b) => (
        <span className="font-mono text-xs">
          {b.material_links
            .map((m) => `${lotNumber(m.material_lot_id)} (${m.quantity_used})`)
            .join(', ')}
        </span>
      ),
    },
    {
      key: 'quarantine_reason',
      header: 'Quarantine reason',
      render: (b) => (
        <span className="whitespace-normal text-xs text-ink-muted">
          {b.quarantine_reason ?? ''}
        </span>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (b) => <BatchActions batch={b} onResult={setActionError} />,
    },
  ];

  return (
    <>
      <PageHeader
        title="Production Batches"
        description="Starting a batch consumes material lots and creates serialised units in one transaction."
        actions={
          can('batch.create') && (
            <Disclosure label="Start batch">{(close) => <BatchForm onDone={close} />}</Disclosure>
          )
        }
      />
      <div className="mb-3 grid grid-cols-1 gap-3 sm:grid-cols-3 lg:max-w-3xl">
        <SelectField
          label="Order"
          value={orderId}
          onChange={(e) => {
            setOrderId(e.target.value);
            resetOffset();
          }}
        >
          <option value="">All orders</option>
          {orders.data?.items.map((o) => (
            <option key={o.id} value={o.id}>
              {o.order_number}
            </option>
          ))}
        </SelectField>
        <SelectField
          label="Machine"
          value={machineId}
          onChange={(e) => {
            setMachineId(e.target.value);
            resetOffset();
          }}
        >
          <option value="">All machines</option>
          {machines.data?.map((m) => (
            <option key={m.id} value={m.id}>
              {m.code}
            </option>
          ))}
        </SelectField>
        <SelectField
          label="Status"
          value={status}
          onChange={(e) => {
            setStatus(e.target.value as BatchStatus | '');
            resetOffset();
          }}
        >
          <option value="">All statuses</option>
          {BATCH_STATUSES.map((s) => (
            <option key={s} value={s}>
              {titleCase(s)}
            </option>
          ))}
        </SelectField>
      </div>
      {highlightedId && (
        <div className="mb-3">
          <InlineNotice tone="info">
            Batch {highlightedId} was opened from an investigation. It is highlighted in the table
            below.
          </InlineNotice>
        </div>
      )}
      {actionError !== null && (
        <div className="mb-3">
          <ErrorNotice error={actionError} />
        </div>
      )}
      <div className="panel">
        {batches.isPending && <LoadingState label="Loading batches" />}
        {batches.isError && (
          <div className="p-4">
            <ErrorState error={batches.error} onRetry={() => void batches.refetch()} />
          </div>
        )}
        {batches.data && (
          <>
            <PageBody loading={batches.isPlaceholderData}>
              <DataTable
                columns={columns}
                rows={batches.data.items}
                rowKey={(b) => b.id}
                caption="Production batches"
                emptyTitle="No batches match these filters"
              />
            </PageBody>
            <Pagination
              total={batches.data.total}
              limit={page.limit}
              offset={page.offset}
              onChange={setPage}
              label="Production batches"
              className="px-4"
            />
          </>
        )}
      </div>
    </>
  );
}
