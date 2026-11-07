import { useState } from 'react';

import { Button } from '@/components/ui/Button';
import type { Column } from '@/components/ui/DataTable';
import { DataTable } from '@/components/ui/DataTable';
import { Disclosure } from '@/components/ui/Disclosure';
import { SelectField } from '@/components/ui/Field';
import { PageHeader } from '@/components/ui/PageHeader';
import { PageBody, Pagination } from '@/components/ui/Pagination';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { ErrorState, InlineNotice, LoadingState } from '@/components/ui/States';
import { useMachines, useOrders, useProducts } from '@/hooks/queries';
import { useAuth } from '@/hooks/useAuth';
import { usePageState } from '@/hooks/usePageState';
import type { OrderStatus, ProductionOrder } from '@/types/api';
import { ORDER_STATUSES } from '@/types/constants';
import { formatDate, formatNumber, titleCase } from '@/utils/format';
import { isOrderEditable } from '@/utils/transitions';

import { OrderForm } from './OrderForm';
import { OrderTransitions } from './OrderTransitions';

export function OrdersPage() {
  const { can } = useAuth();
  const [status, setStatus] = useState<OrderStatus | ''>('');
  const [editing, setEditing] = useState<ProductionOrder | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const { page, setPage, resetOffset } = usePageState();
  const orders = useOrders({ status, ...page });
  const products = useProducts();
  const machines = useMachines();

  const productName = (id: number) => products.data?.find((p) => p.id === id)?.code ?? `#${id}`;
  const machineCode = (id: number | null) =>
    id === null ? 'Unassigned' : (machines.data?.find((m) => m.id === id)?.code ?? `#${id}`);

  const columns: Column<ProductionOrder>[] = [
    {
      key: 'order_number',
      header: 'Order',
      render: (o) => <span className="font-mono font-medium">{o.order_number}</span>,
    },
    { key: 'product', header: 'Product', render: (o) => productName(o.product_id) },
    {
      key: 'machine',
      header: 'Machine',
      render: (o) => <span className="font-mono">{machineCode(o.machine_id)}</span>,
    },
    { key: 'status', header: 'Status', render: (o) => <StatusBadge status={o.status} /> },
    {
      key: 'progress',
      header: 'Completed / planned',
      align: 'right',
      render: (o) => `${formatNumber(o.quantity_completed)} / ${formatNumber(o.quantity_planned)}`,
    },
    { key: 'due_date', header: 'Due', render: (o) => formatDate(o.due_date) || '' },
    {
      key: 'actions',
      header: 'Actions',
      render: (o) => (
        <div className="flex flex-wrap items-center gap-1.5">
          {can('order.transition') && <OrderTransitions order={o} onResult={setActionError} />}
          {can('order.edit') && isOrderEditable(o.status) && (
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setEditing(o)}
              aria-label={`Edit ${o.order_number}`}
            >
              Edit
            </Button>
          )}
          {!can('order.transition') && !can('order.edit') && (
            <span className="text-xs text-ink-faint">Read only</span>
          )}
        </div>
      ),
    },
  ];

  return (
    <>
      <PageHeader
        title="Production Orders"
        description="Orders move Planned to Released to In progress to Completed; only legal moves are offered."
        actions={
          can('order.create') && (
            <Disclosure label="New order">{(close) => <OrderForm onDone={close} />}</Disclosure>
          )
        }
      />
      {editing && (
        <div className="mb-4">
          <p className="text-sm font-medium text-ink">Editing {editing.order_number}</p>
          <OrderForm key={editing.id} order={editing} onDone={() => setEditing(null)} />
        </div>
      )}
      <div className="mb-3 max-w-xs">
        <SelectField
          label="Status filter"
          value={status}
          onChange={(e) => {
            setStatus(e.target.value as OrderStatus | '');
            resetOffset();
          }}
        >
          <option value="">All statuses</option>
          {ORDER_STATUSES.map((s) => (
            <option key={s} value={s}>
              {titleCase(s)}
            </option>
          ))}
        </SelectField>
      </div>
      {actionError && (
        <div className="mb-3">
          <InlineNotice tone="error">{actionError}</InlineNotice>
        </div>
      )}
      <div className="panel">
        {orders.isPending && <LoadingState label="Loading orders" />}
        {orders.isError && (
          <div className="p-4">
            <ErrorState error={orders.error} onRetry={() => void orders.refetch()} />
          </div>
        )}
        {orders.data && (
          <>
            <PageBody loading={orders.isPlaceholderData}>
              <DataTable
                columns={columns}
                rows={orders.data.items}
                rowKey={(o) => o.id}
                caption="Production orders"
                emptyTitle="No orders match this filter"
              />
            </PageBody>
            <Pagination
              total={orders.data.total}
              limit={page.limit}
              offset={page.offset}
              onChange={setPage}
              label="Production orders"
              className="px-4"
            />
          </>
        )}
      </div>
    </>
  );
}
