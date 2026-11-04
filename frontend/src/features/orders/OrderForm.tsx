import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import type { FormEvent } from 'react';

import { Button } from '@/components/ui/Button';
import { SelectField, TextField } from '@/components/ui/Field';
import { ErrorState, InlineNotice } from '@/components/ui/States';
import { invalidateProduction } from '@/hooks/invalidate';
import { useMachines, useProducts } from '@/hooks/queries';
import { productionApi } from '@/services/api';
import type { ProductionOrder } from '@/types/api';
import { describeError } from '@/utils/errors';

interface OrderFormProps {
  /** When set, the form edits this order (machine, quantity, due date only). */
  order?: ProductionOrder;
  onDone: () => void;
}

export function OrderForm({ order, onDone }: OrderFormProps) {
  const queryClient = useQueryClient();
  const products = useProducts();
  const machines = useMachines();
  const [orderNumber, setOrderNumber] = useState(order?.order_number ?? '');
  const [productId, setProductId] = useState(order ? String(order.product_id) : '');
  const [machineId, setMachineId] = useState(order?.machine_id ? String(order.machine_id) : '');
  const [quantity, setQuantity] = useState(order ? String(order.quantity_planned) : '');
  const [dueDate, setDueDate] = useState(order?.due_date ?? '');
  const [error, setError] = useState<string | null>(null);

  const save = useMutation({
    mutationFn: () => {
      const machine = machineId ? Number(machineId) : null;
      const due = dueDate || null;
      if (order) {
        return productionApi.updateOrder(order.id, {
          machine_id: machine,
          quantity_planned: Number(quantity),
          due_date: due,
        });
      }
      return productionApi.createOrder({
        order_number: orderNumber.trim().toUpperCase(),
        product_id: Number(productId),
        machine_id: machine,
        quantity_planned: Number(quantity),
        due_date: due,
      });
    },
    onSuccess: () => {
      invalidateProduction(queryClient);
      onDone();
    },
    onError: (cause) => setError(describeError(cause)),
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    save.mutate();
  }

  const lookupError = products.error ?? machines.error;
  if (lookupError) {
    return (
      <div className="mt-3">
        <ErrorState
          error={lookupError}
          title="Could not load products and machines"
          onRetry={() => {
            void products.refetch();
            void machines.refetch();
          }}
        />
      </div>
    );
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="panel mt-3 grid grid-cols-1 gap-3 p-4 md:grid-cols-2 xl:grid-cols-5"
      aria-label={order ? 'Edit order' : 'Create order'}
    >
      <TextField
        label="Order number"
        value={orderNumber}
        onChange={(e) => setOrderNumber(e.target.value)}
        disabled={Boolean(order)}
        required={!order}
        pattern="[A-Z0-9][A-Z0-9_\-]{1,29}"
        hint="Uppercase letters, digits, dash, underscore."
      />
      <SelectField
        label="Product"
        value={productId}
        onChange={(e) => setProductId(e.target.value)}
        disabled={Boolean(order)}
        required={!order}
      >
        <option value="">Select a product</option>
        {products.data?.map((p) => (
          <option key={p.id} value={p.id}>
            {p.code} · {p.name}
          </option>
        ))}
      </SelectField>
      <SelectField
        label="Machine"
        value={machineId}
        onChange={(e) => setMachineId(e.target.value)}
        hint="Required before release."
      >
        <option value="">Unassigned</option>
        {machines.data?.map((m) => (
          <option key={m.id} value={m.id}>
            {m.code} · {m.name}
          </option>
        ))}
      </SelectField>
      <TextField
        label="Quantity planned"
        type="number"
        min={1}
        max={100000}
        value={quantity}
        onChange={(e) => setQuantity(e.target.value)}
        required
      />
      <TextField
        label="Due date"
        type="date"
        value={dueDate}
        onChange={(e) => setDueDate(e.target.value)}
      />
      {error && (
        <div className="md:col-span-2 xl:col-span-5">
          <InlineNotice tone="error">{error}</InlineNotice>
        </div>
      )}
      <div className="flex gap-2 md:col-span-2 xl:col-span-5">
        <Button type="submit" variant="primary" busy={save.isPending}>
          {order ? 'Save changes' : 'Create order'}
        </Button>
        <Button onClick={onDone}>Cancel</Button>
      </div>
    </form>
  );
}
