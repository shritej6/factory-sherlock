import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import type { FormEvent } from 'react';

import { Button } from '@/components/ui/Button';
import { SelectField, TextField } from '@/components/ui/Field';
import { InlineNotice } from '@/components/ui/States';
import { invalidateProduction } from '@/hooks/invalidate';
import { queryKeys } from '@/hooks/queries';
import { catalogApi } from '@/services/api';
import type { Machine, MachineStatus } from '@/types/api';
import { describeError } from '@/utils/errors';
import { titleCase } from '@/utils/format';
import { legalMachineMoves } from '@/utils/transitions';

export function MachineStatusForm({ machine }: { machine: Machine }) {
  const queryClient = useQueryClient();
  const moves = legalMachineMoves(machine.status);
  const [status, setStatus] = useState<MachineStatus | ''>(moves[0] ?? '');
  const [reason, setReason] = useState('');
  const [fieldErrors, setFieldErrors] = useState<{ status?: string; reason?: string }>({});
  const [message, setMessage] = useState<{ tone: 'error' | 'success'; text: string } | null>(null);

  const change = useMutation({
    mutationFn: () =>
      catalogApi.changeMachineStatus(machine.id, { status: status as MachineStatus, reason }),
    onSuccess: (updated) => {
      setMessage({ tone: 'success', text: `${updated.code} is now ${titleCase(updated.status)}.` });
      setReason('');
      setStatus(legalMachineMoves(updated.status)[0] ?? '');
      invalidateProduction(queryClient);
      void queryClient.invalidateQueries({ queryKey: queryKeys.machineEvents(machine.id) });
    },
    onError: (cause) => setMessage({ tone: 'error', text: describeError(cause) }),
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const errors: { status?: string; reason?: string } = {};
    if (!status) errors.status = 'Choose the status to move to.';
    if (!reason.trim()) errors.reason = 'Enter a reason; it is recorded on the event timeline.';
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) return;
    setMessage(null);
    change.mutate();
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="flex flex-col gap-3"
      aria-label="Change machine status"
      noValidate
    >
      <SelectField
        label="New status"
        value={status}
        onChange={(e) => setStatus(e.target.value as MachineStatus)}
        error={fieldErrors.status}
        required
      >
        {moves.length === 0 && <option value="">No transitions available</option>}
        {moves.map((move) => (
          <option key={move} value={move}>
            {titleCase(move)}
          </option>
        ))}
      </SelectField>
      <TextField
        label="Reason"
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        maxLength={255}
        required
        error={fieldErrors.reason}
        hint="Recorded on the machine event timeline."
      />
      {message && <InlineNotice tone={message.tone}>{message.text}</InlineNotice>}
      <Button type="submit" variant="primary" busy={change.isPending} disabled={moves.length === 0}>
        Apply status
      </Button>
    </form>
  );
}
