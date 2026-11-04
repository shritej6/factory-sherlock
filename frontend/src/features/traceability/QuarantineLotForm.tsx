import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import type { FormEvent } from 'react';

import { Button } from '@/components/ui/Button';
import { SelectField, TextField } from '@/components/ui/Field';
import { ErrorState, InlineNotice } from '@/components/ui/States';
import { invalidateProduction } from '@/hooks/invalidate';
import { useMaterialLots } from '@/hooks/queries';
import { traceabilityApi } from '@/services/api';
import { describeError } from '@/utils/errors';

export function QuarantineLotForm() {
  const queryClient = useQueryClient();
  const lots = useMaterialLots();
  const [lotId, setLotId] = useState('');
  const [reason, setReason] = useState('');
  const [message, setMessage] = useState<{ tone: 'error' | 'success'; text: string } | null>(null);

  const quarantine = useMutation({
    mutationFn: () => traceabilityApi.quarantineLot(Number(lotId), { reason: reason.trim() }),
    onSuccess: (result) => {
      setMessage({
        tone: 'success',
        text: `Lot ${result.lot.lot_number} is quarantined; ${result.quarantined_batches.length} batch(es) were quarantined with it.`,
      });
      setReason('');
      invalidateProduction(queryClient);
    },
    onError: (cause) => setMessage({ tone: 'error', text: describeError(cause) }),
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    quarantine.mutate();
  }

  if (lots.isError) {
    return (
      <ErrorState
        error={lots.error}
        title="Could not load material lots"
        onRetry={() => void lots.refetch()}
      />
    );
  }

  const candidates = lots.data?.filter((lot) => lot.status !== 'QUARANTINED') ?? [];

  return (
    <form
      onSubmit={handleSubmit}
      className="flex flex-col gap-3"
      aria-label="Quarantine material lot"
    >
      <SelectField
        label="Material lot"
        value={lotId}
        onChange={(e) => setLotId(e.target.value)}
        required
      >
        <option value="">Select a lot</option>
        {candidates.map((lot) => (
          <option key={lot.id} value={lot.id}>
            {lot.lot_number} · {lot.material_name} · {lot.supplier}
          </option>
        ))}
      </SelectField>
      <TextField
        label="Reason"
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        minLength={5}
        maxLength={255}
        required
        hint="Every batch that consumed the lot is quarantined in the same transaction."
      />
      {message && <InlineNotice tone={message.tone}>{message.text}</InlineNotice>}
      <Button
        type="submit"
        variant="danger"
        busy={quarantine.isPending}
        disabled={!lotId || reason.trim().length < 5}
      >
        Quarantine lot and its batches
      </Button>
    </form>
  );
}
