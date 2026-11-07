import { useMutation, useQueryClient } from '@tanstack/react-query';

import { Button } from '@/components/ui/Button';
import { invalidateProduction } from '@/hooks/invalidate';
import { productionApi } from '@/services/api';
import type { OrderStatus, ProductionOrder } from '@/types/api';
import { titleCase } from '@/utils/format';
import { legalOrderMoves } from '@/utils/transitions';

const MOVE_LABELS: Record<OrderStatus, string> = {
  PLANNED: 'Plan',
  RELEASED: 'Release',
  IN_PROGRESS: 'Start',
  COMPLETED: 'Complete',
  CANCELLED: 'Cancel',
};

interface OrderTransitionsProps {
  order: ProductionOrder;
  /** Receives the failure, or null once a later action succeeds. */
  onResult: (error: unknown) => void;
}

export function OrderTransitions({ order, onResult }: OrderTransitionsProps) {
  const queryClient = useQueryClient();
  const moves = legalOrderMoves(order.status);
  const change = useMutation({
    mutationFn: (status: OrderStatus) => productionApi.changeOrderStatus(order.id, status),
    onSuccess: () => {
      onResult(null);
      invalidateProduction(queryClient);
    },
    onError: onResult,
  });

  if (moves.length === 0) return <span className="text-xs text-ink-faint">Terminal state</span>;
  return (
    <div
      className="flex flex-wrap gap-1.5"
      role="group"
      aria-label={`Transitions for ${order.order_number}`}
    >
      {moves.map((move) => (
        <Button
          key={move}
          size="sm"
          variant={move === 'CANCELLED' ? 'danger' : 'secondary'}
          busy={change.isPending && change.variables === move}
          onClick={() => change.mutate(move)}
          title={`Move to ${titleCase(move)}`}
        >
          {MOVE_LABELS[move]}
        </Button>
      ))}
    </div>
  );
}
