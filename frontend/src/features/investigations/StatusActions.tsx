import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import type { FormEvent } from 'react';

import { Button } from '@/components/ui/Button';
import { TextAreaField } from '@/components/ui/Field';
import { InlineNotice } from '@/components/ui/States';
import { queryKeys } from '@/hooks/queries';
import { investigationApi } from '@/services/api';
import type { Investigation, InvestigationStatus } from '@/types/api';
import { describeError } from '@/utils/errors';
import { legalInvestigationMoves } from '@/utils/transitions';

export function StatusActions({ investigation }: { investigation: Investigation }) {
  const queryClient = useQueryClient();
  const [closing, setClosing] = useState(false);
  const [conclusion, setConclusion] = useState(investigation.conclusion ?? '');
  const [error, setError] = useState<string | null>(null);
  const moves = legalInvestigationMoves(investigation.status);

  const change = useMutation({
    mutationFn: (status: InvestigationStatus) =>
      investigationApi.changeStatus(investigation.id, {
        status,
        conclusion: status === 'CLOSED' ? conclusion.trim() : null,
      }),
    onSuccess: () => {
      setClosing(false);
      setError(null);
      void queryClient.invalidateQueries({ queryKey: queryKeys.investigations });
      void queryClient.invalidateQueries({ queryKey: queryKeys.investigation(investigation.id) });
    },
    onError: (cause) => setError(describeError(cause)),
  });

  if (moves.length === 0)
    return <p className="text-sm text-ink-muted">This case is closed and cannot be reopened.</p>;

  function submitClose(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!conclusion.trim()) return;
    change.mutate('CLOSED');
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap gap-2">
        {moves.includes('IN_REVIEW') && (
          <Button
            busy={change.isPending && change.variables === 'IN_REVIEW'}
            onClick={() => change.mutate('IN_REVIEW')}
          >
            Mark in review
          </Button>
        )}
        {moves.includes('OPEN') && (
          <Button
            busy={change.isPending && change.variables === 'OPEN'}
            onClick={() => change.mutate('OPEN')}
          >
            Return to open
          </Button>
        )}
        {moves.includes('CLOSED') && !closing && (
          <Button variant="primary" onClick={() => setClosing(true)}>
            Close with conclusion
          </Button>
        )}
      </div>
      {closing && (
        <form
          onSubmit={submitClose}
          className="flex flex-col gap-2"
          aria-label="Close investigation"
        >
          <TextAreaField
            label="Conclusion"
            value={conclusion}
            onChange={(e) => setConclusion(e.target.value)}
            maxLength={4000}
            required
            hint="Required. State what was found and what action was taken."
          />
          <div className="flex gap-2">
            <Button
              type="submit"
              variant="primary"
              busy={change.isPending && change.variables === 'CLOSED'}
              disabled={!conclusion.trim()}
            >
              Close case
            </Button>
            <Button onClick={() => setClosing(false)}>Cancel</Button>
          </div>
        </form>
      )}
      {error && <InlineNotice tone="error">{error}</InlineNotice>}
    </div>
  );
}
