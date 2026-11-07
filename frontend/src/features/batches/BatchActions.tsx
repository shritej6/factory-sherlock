import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useRef, useState } from 'react';

import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/Field';
import { invalidateProduction } from '@/hooks/invalidate';
import { useAuth } from '@/hooks/useAuth';
import { productionApi } from '@/services/api';
import type { ProductionBatch } from '@/types/api';
import { legalBatchMoves } from '@/utils/transitions';

interface BatchActionsProps {
  batch: ProductionBatch;
  /** Receives the failure, or null once a later action succeeds. */
  onResult: (error: unknown) => void;
}

export function BatchActions({ batch, onResult }: BatchActionsProps) {
  const { can } = useAuth();
  const queryClient = useQueryClient();
  const [reason, setReason] = useState('');
  const [quarantining, setQuarantining] = useState(false);
  const quarantineTrigger = useRef<HTMLButtonElement>(null);
  const moves = legalBatchMoves(batch.status);

  const succeed = () => {
    onResult(null);
    invalidateProduction(queryClient);
  };
  const complete = useMutation({
    mutationFn: () => productionApi.completeBatch(batch.id),
    onSuccess: succeed,
    onError: onResult,
  });
  const quarantine = useMutation({
    mutationFn: () => productionApi.quarantineBatch(batch.id, { reason }),
    onSuccess: () => {
      setQuarantining(false);
      succeed();
    },
    onError: onResult,
  });

  // Cancelling removes the focused button, so focus goes back to the control that opened the form.
  function cancelQuarantine() {
    setQuarantining(false);
    requestAnimationFrame(() => quarantineTrigger.current?.focus());
  }

  const canComplete = can('batch.complete') && moves.includes('COMPLETED');
  const canQuarantine = can('batch.quarantine') && moves.includes('QUARANTINED');
  if (!canComplete && !canQuarantine)
    return <span className="text-xs text-ink-faint">No actions</span>;

  return (
    <div className="flex flex-wrap items-end gap-1.5">
      {canComplete && (
        <Button
          size="sm"
          busy={complete.isPending}
          onClick={() => complete.mutate()}
          aria-label={`Complete batch ${batch.batch_number}`}
        >
          Complete
        </Button>
      )}
      {canQuarantine && !quarantining && (
        <Button
          ref={quarantineTrigger}
          size="sm"
          variant="danger"
          onClick={() => setQuarantining(true)}
          aria-label={`Quarantine batch ${batch.batch_number}`}
        >
          Quarantine
        </Button>
      )}
      {canQuarantine && quarantining && (
        <form
          className="flex flex-wrap items-end gap-1.5"
          aria-label={`Quarantine batch ${batch.batch_number}`}
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
            autoFocus
            className="min-w-56"
          />
          <Button
            size="sm"
            type="submit"
            variant="danger"
            busy={quarantine.isPending}
            disabled={reason.trim().length < 5}
            aria-label={`Confirm quarantine of batch ${batch.batch_number}`}
          >
            Confirm
          </Button>
          <Button
            size="sm"
            onClick={cancelQuarantine}
            aria-label={`Cancel quarantine of batch ${batch.batch_number}`}
          >
            Cancel
          </Button>
        </form>
      )}
    </div>
  );
}
