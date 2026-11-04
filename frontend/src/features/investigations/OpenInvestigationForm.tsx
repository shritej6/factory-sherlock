import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import type { FormEvent } from 'react';
import { useNavigate } from 'react-router';

import { Button } from '@/components/ui/Button';
import { SelectField, TextField } from '@/components/ui/Field';
import { ErrorState, InlineNotice } from '@/components/ui/States';
import { queryKeys, useMachines } from '@/hooks/queries';
import { investigationApi } from '@/services/api';
import { DEFAULT_WINDOW_END, DEFAULT_WINDOW_START } from '@/types/constants';
import { describeError } from '@/utils/errors';
import { toApiDateTime } from '@/utils/format';

export function OpenInvestigationForm({ onDone }: { onDone: () => void }) {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const machines = useMachines();
  const [title, setTitle] = useState('');
  const [machineId, setMachineId] = useState('');
  const [windowStart, setWindowStart] = useState(DEFAULT_WINDOW_START);
  const [windowEnd, setWindowEnd] = useState(DEFAULT_WINDOW_END);
  const [error, setError] = useState<string | null>(null);

  const open = useMutation({
    mutationFn: () =>
      investigationApi.open({
        title: title.trim(),
        machine_id: machineId ? Number(machineId) : null,
        window_start: toApiDateTime(windowStart),
        window_end: toApiDateTime(windowEnd),
      }),
    onSuccess: (investigation) => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.investigations });
      onDone();
      navigate(`/investigations/${investigation.id}`);
    },
    onError: (cause) => setError(describeError(cause)),
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (windowEnd <= windowStart) {
      setError('The window end must be after the window start.');
      return;
    }
    open.mutate();
  }

  if (machines.isError) {
    return (
      <div className="mt-3">
        <ErrorState
          error={machines.error}
          title="Could not load machines"
          onRetry={() => void machines.refetch()}
        />
      </div>
    );
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="panel mt-3 grid grid-cols-1 gap-3 p-4 md:grid-cols-2 xl:grid-cols-4"
      aria-label="Open investigation"
    >
      <TextField
        label="Title"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        minLength={3}
        maxLength={150}
        required
        className="xl:col-span-1"
      />
      <SelectField
        label="Machine"
        value={machineId}
        onChange={(e) => setMachineId(e.target.value)}
        hint="Leave empty to compare the whole fleet."
      >
        <option value="">All machines</option>
        {machines.data?.map((m) => (
          <option key={m.id} value={m.id}>
            {m.code} · {m.name}
          </option>
        ))}
      </SelectField>
      <TextField
        label="Window start"
        type="datetime-local"
        value={windowStart}
        onChange={(e) => setWindowStart(e.target.value)}
        required
      />
      <TextField
        label="Window end"
        type="datetime-local"
        value={windowEnd}
        onChange={(e) => setWindowEnd(e.target.value)}
        required
      />
      {error && (
        <div className="md:col-span-2 xl:col-span-4">
          <InlineNotice tone="error">{error}</InlineNotice>
        </div>
      )}
      <div className="flex gap-2 md:col-span-2 xl:col-span-4">
        <Button
          type="submit"
          variant="primary"
          busy={open.isPending}
          disabled={title.trim().length < 3}
        >
          Run the rules and open the case
        </Button>
        <Button onClick={onDone}>Cancel</Button>
      </div>
    </form>
  );
}
