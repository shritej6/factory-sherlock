import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';

import type { Column } from '@/components/ui/DataTable';
import { DataTable } from '@/components/ui/DataTable';
import { PageHeader } from '@/components/ui/PageHeader';
import { Panel } from '@/components/ui/Panel';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { EmptyState, ErrorState, LoadingState } from '@/components/ui/States';
import { useAuth } from '@/hooks/useAuth';
import { traceabilityApi } from '@/services/api';
import type { BackwardTraceRow, ForwardTraceRow } from '@/types/api';
import { isNotFound } from '@/utils/errors';
import { formatDateTime, formatNumber, formatPercent } from '@/utils/format';

import { QuarantineLotForm } from './QuarantineLotForm';
import { TraceSearchForm } from './TraceSearchForm';

const FORWARD_COLUMNS: Column<ForwardTraceRow>[] = [
  {
    key: 'batch_number',
    header: 'Batch',
    render: (r) => <span className="font-mono">{r.batch_number}</span>,
  },
  { key: 'batch_status', header: 'Status', render: (r) => <StatusBadge status={r.batch_status} /> },
  {
    key: 'machine_code',
    header: 'Machine',
    render: (r) => <span className="font-mono">{r.machine_code}</span>,
  },
  {
    key: 'order_number',
    header: 'Order',
    render: (r) => <span className="font-mono">{r.order_number}</span>,
  },
  { key: 'product_name', header: 'Product' },
  { key: 'started_at', header: 'Started', render: (r) => formatDateTime(r.started_at) },
  {
    key: 'quantity_used',
    header: 'Qty used',
    align: 'right',
    render: (r) => formatNumber(r.quantity_used),
  },
  {
    key: 'units_produced',
    header: 'Units',
    align: 'right',
    render: (r) => formatNumber(r.units_produced),
  },
  {
    key: 'units_failed',
    header: 'Failed units',
    align: 'right',
    render: (r) =>
      `${formatNumber(r.units_failed)} (${formatPercent(r.units_produced ? r.units_failed / r.units_produced : 0)})`,
  },
];

const BACKWARD_COLUMNS: Column<BackwardTraceRow>[] = [
  {
    key: 'lot_number',
    header: 'Material lot',
    render: (r) => <span className="font-mono">{r.lot_number ?? 'none'}</span>,
  },
  { key: 'material_name', header: 'Material' },
  { key: 'supplier', header: 'Supplier' },
  {
    key: 'lot_status',
    header: 'Lot status',
    render: (r) => (r.lot_status ? <StatusBadge status={r.lot_status} /> : ''),
  },
];

export function TraceabilityPage() {
  const { can } = useAuth();
  const [lotNumber, setLotNumber] = useState<string | null>(null);
  const [serialNumber, setSerialNumber] = useState<string | null>(null);
  const forward = useQuery({
    queryKey: ['trace', 'forward', lotNumber],
    queryFn: () => traceabilityApi.forward(lotNumber ?? ''),
    enabled: lotNumber !== null,
    retry: false,
  });
  const backward = useQuery({
    queryKey: ['trace', 'backward', serialNumber],
    queryFn: () => traceabilityApi.backward(serialNumber ?? ''),
    enabled: serialNumber !== null,
    retry: false,
  });
  const origin = backward.data?.lineage[0];

  return (
    <>
      <PageHeader
        title="Material Traceability"
        description="Follow a material lot forward into batches, or trace a serial number back to its origins."
      />
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1fr_360px]">
        <div className="flex min-w-0 flex-col gap-4">
          <Panel
            title="Forward trace"
            description="Which batches consumed a material lot, and how many of their units failed."
          >
            <TraceSearchForm
              label="Lot number"
              hint="For example L201."
              buttonLabel="Trace lot"
              busy={forward.isFetching}
              onSearch={setLotNumber}
            />
            <div className="mt-4">
              {lotNumber === null && <EmptyState title="Enter a lot number to begin" />}
              {forward.isPending && lotNumber !== null && <LoadingState label="Tracing lot" />}
              {forward.isError && isNotFound(forward.error) && (
                <EmptyState
                  title={`Lot ${lotNumber} was not found`}
                  hint="Check the lot number and try again."
                />
              )}
              {forward.isError && !isNotFound(forward.error) && (
                <ErrorState error={forward.error} onRetry={() => void forward.refetch()} />
              )}
              {forward.data && (
                <DataTable
                  columns={FORWARD_COLUMNS}
                  rows={forward.data.batches}
                  rowKey={(r) => r.batch_id}
                  caption={`Batches that consumed lot ${forward.data.lot_number}`}
                  emptyTitle={`Lot ${forward.data.lot_number} has not been consumed by any batch`}
                />
              )}
            </div>
          </Panel>
          <Panel
            title="Backward trace"
            description="The batch, machine, order, product, material lots, and inspection results behind a serial number."
          >
            <TraceSearchForm
              label="Serial number"
              hint="For example SIM0001-CNC-03-03-B04-U0001."
              buttonLabel="Trace unit"
              busy={backward.isFetching}
              onSearch={setSerialNumber}
            />
            <div className="mt-4">
              {serialNumber === null && <EmptyState title="Enter a serial number to begin" />}
              {backward.isPending && serialNumber !== null && <LoadingState label="Tracing unit" />}
              {backward.isError && isNotFound(backward.error) && (
                <EmptyState
                  title={`Unit ${serialNumber} was not found`}
                  hint="Serial numbers follow the pattern ORDER-Bnn-Unnnn."
                />
              )}
              {backward.isError && !isNotFound(backward.error) && (
                <ErrorState error={backward.error} onRetry={() => void backward.refetch()} />
              )}
              {origin && (
                <>
                  <dl className="mb-4 grid grid-cols-2 gap-x-6 gap-y-2 text-sm md:grid-cols-4">
                    <div>
                      <dt className="text-xs text-ink-muted">Serial</dt>
                      <dd className="font-mono">{origin.serial_number}</dd>
                    </div>
                    <div>
                      <dt className="text-xs text-ink-muted">Produced</dt>
                      <dd>{formatDateTime(origin.produced_at)}</dd>
                    </div>
                    <div>
                      <dt className="text-xs text-ink-muted">Batch</dt>
                      <dd className="flex items-center gap-2 font-mono">
                        {origin.batch_number} <StatusBadge status={origin.batch_status} />
                      </dd>
                    </div>
                    <div>
                      <dt className="text-xs text-ink-muted">Machine</dt>
                      <dd className="font-mono">{origin.machine_code}</dd>
                    </div>
                    <div>
                      <dt className="text-xs text-ink-muted">Order</dt>
                      <dd className="font-mono">{origin.order_number}</dd>
                    </div>
                    <div>
                      <dt className="text-xs text-ink-muted">Product</dt>
                      <dd>{origin.product_name}</dd>
                    </div>
                    <div className="col-span-2">
                      <dt className="text-xs text-ink-muted">Inspection summary</dt>
                      <dd className="font-mono text-xs">
                        {origin.inspection_summary ?? 'Not inspected'}
                      </dd>
                    </div>
                  </dl>
                  <DataTable
                    columns={BACKWARD_COLUMNS}
                    rows={backward.data?.lineage ?? []}
                    rowKey={(r, i) => `${r.lot_number ?? 'none'}-${i}`}
                    caption="Material lots used by the unit's batch"
                  />
                </>
              )}
            </div>
          </Panel>
        </div>
        <Panel title="Quarantine a material lot" className="self-start">
          {can('lot.quarantine') ? (
            <QuarantineLotForm />
          ) : (
            <p className="text-sm text-ink-muted">
              Engineers and administrators can quarantine lots.
            </p>
          )}
        </Panel>
      </div>
    </>
  );
}
