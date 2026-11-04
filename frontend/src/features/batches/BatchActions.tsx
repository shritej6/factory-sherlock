import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/Field';
import { invalidateProduction } from '@/hooks/invalidate';
import { useAuth } from '@/hooks/useAuth';
import { productionApi } from '@/services/api';
import type { ProductionBatch } from '@/types/api';
import { describeError } from '@/utils/errors';
import { legalBatchMoves } from '@/utils/transitions';

interface BatchActionsProps {
  batch: ProductionBatch;
  /** Receives the failure message, or null once a later action succeeds. */
  onResult: (message: string | null) => void;
}

export function BatchActions({ batch, onResult }: BatchActionsProps) {
  const { can } = useAuth();
  const queryClient = useQueryClient();
  const [reason, setReason] = useState('');
  const [quarantining, setQuarantining] = useState(false);
  const moves = legalBatchMoves(batch.status);

  const succeed = () => {
    onResult(null);
    invalidateProduction(queryClient);
  };
  const complete = useMutation({
    mutationFn: () => productionApi.completeBatch(batch.id),
    onSuccess: succeed,
    onError: (cause) => onResult(describeError(cause)),
  });
  const quarantine = useMutation({
    mutationFn: () => productionApi.quarantineBatch(batch.id, { reason }),
    onSuccess: () => {
      setQuarantining(false);
      succeed();
    },
    onError: (cause) => onResult(describeError(cause)),
  });

  const canComplete = can('batch.complete') && moves.includes('COMPLETED');
  const canQuarantine = can('batch.quarantine') && moves.includes('QUARANTINED');
  if (!canComplete && !canQuarantine)
    return <span className="text-xs text-ink-faint">No actions</span>;

  return (
    <div className="flex flex-wrap items-end gap-1.5">
      {canComplete && (
        <Button size="sm" busy={complete.isPending} onClick={() => complete.mutate()}>
          Complete
        </Button>
      )}
      {canQuarantine && !quarantining && (
        <Button size="sm" variant="danger" onClick={() => setQuarantining(true)}>
          Quarantine
        </Button>
      )}
      {canQuarantine && quarantining && (
        <form
          className="flex flex-wrap items-end gap-1.5"
          onSubmit={(event) => {
            event.preventDefault();
            quarantine.mutate();
          }}
        >
          <TextField
            label="Reason"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            minLength={5}
            maxLength={255}
            required
            className="min-w-56"
          />
          <Button
            size="sm"
            type="submit"
            variant="danger"
            busy={quarantine.isPending}
            disabled={reason.trim().length < 5}
          >
            Confirm
          </Button>
          <Button size="sm" onClick={() => setQuarantining(false)}>
            Cancel
          </Button>
        </form>
      )}
    </div>
  );
}
