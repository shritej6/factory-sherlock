import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import type { FormEvent } from 'react';

import { Button } from '@/components/ui/Button';
import { SelectField, TextField } from '@/components/ui/Field';
import { ErrorNotice, ErrorState } from '@/components/ui/States';
import { invalidateProduction } from '@/hooks/invalidate';
import { useMaterialLots, useProducibleOrders } from '@/hooks/queries';
import { productionApi } from '@/services/api';
import { formatNumber } from '@/utils/format';

interface MaterialLine {
  key: number;
  lotId: string;
  quantity: string;
}

export function BatchForm({ onDone }: { onDone: () => void }) {
  const queryClient = useQueryClient();
  const orders = useProducibleOrders();
  const lots = useMaterialLots();
  const [orderId, setOrderId] = useState('');
  const [quantity, setQuantity] = useState('');
  const [lines, setLines] = useState<MaterialLine[]>([{ key: 1, lotId: '', quantity: '' }]);
  const [error, setError] = useState<unknown>(null);

  const producible = orders.data ?? [];
  const availableLots = lots.data?.filter((l) => l.status === 'AVAILABLE') ?? [];

  const create = useMutation({
    mutationFn: () =>
      productionApi.createBatch({
        production_order_id: Number(orderId),
        quantity: Number(quantity),
        materials: lines.map((line) => ({
          material_lot_id: Number(line.lotId),
          quantity_used: line.quantity,
        })),
      }),
    onSuccess: () => {
      invalidateProduction(queryClient);
      onDone();
    },
    onError: setError,
  });

  function updateLine(key: number, patch: Partial<MaterialLine>) {
    setLines((current) => current.map((line) => (line.key === key ? { ...line, ...patch } : line)));
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (lines.some((line) => !line.lotId || !line.quantity)) {
      setError(new Error('Every material line needs a lot and a quantity.'));
      return;
    }
    create.mutate();
  }

  const lookupError = orders.error ?? lots.error;
  if (lookupError) {
    return (
      <div className="mt-3">
        <ErrorState
          error={lookupError}
          title="Could not load orders and material lots"
          onRetry={() => {
            void orders.refetch();
            void lots.refetch();
          }}
        />
      </div>
    );
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="panel mt-3 flex flex-col gap-3 p-4"
      aria-label="Create batch"
    >
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <SelectField
          label="Production order"
          value={orderId}
          onChange={(e) => setOrderId(e.target.value)}
          required
          hint="Only released or in-progress orders can start batches."
        >
          <option value="">Select an order</option>
          {producible.map((o) => (
            <option key={o.id} value={o.id}>
              {o.order_number} · {formatNumber(o.quantity_planned - o.quantity_completed)} remaining
            </option>
          ))}
        </SelectField>
        <TextField
          label="Quantity"
          type="number"
          min={1}
          max={10000}
          value={quantity}
          onChange={(e) => setQuantity(e.target.value)}
          required
        />
      </div>
      <fieldset className="flex flex-col gap-2">
        <legend className="text-xs font-medium text-ink-muted">Material lots consumed</legend>
        {lines.map((line, index) => (
          <div
            key={line.key}
            className="grid grid-cols-1 gap-2 md:grid-cols-[1fr_160px_auto] md:items-end"
          >
            <SelectField
              label={`Lot ${index + 1}`}
              value={line.lotId}
              onChange={(e) => updateLine(line.key, { lotId: e.target.value })}
              required
            >
              <option value="">Select a lot</option>
              {availableLots.map((lot) => (
                <option key={lot.id} value={lot.id}>
                  {lot.lot_number} · {lot.material_name}
                </option>
              ))}
            </SelectField>
            <TextField
              label="Quantity used"
              type="number"
              min="0.01"
              step="0.01"
              value={line.quantity}
              onChange={(e) => updateLine(line.key, { quantity: e.target.value })}
              required
            />
            <Button
              size="sm"
              disabled={lines.length === 1}
              onClick={() => setLines((c) => c.filter((l) => l.key !== line.key))}
              aria-label={`Remove lot ${index + 1}`}
            >
              Remove
            </Button>
          </div>
        ))}
        <div>
          <Button
            size="sm"
            onClick={() => setLines((c) => [...c, { key: Date.now(), lotId: '', quantity: '' }])}
          >
            Add lot
          </Button>
        </div>
      </fieldset>
      {error !== null && <ErrorNotice error={error} />}
      <div className="flex gap-2">
        <Button type="submit" variant="primary" busy={create.isPending}>
          Start batch
        </Button>
        <Button onClick={onDone}>Cancel</Button>
      </div>
    </form>
  );
}
