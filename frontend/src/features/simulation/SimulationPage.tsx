import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import type { FormEvent } from 'react';

import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/Field';
import { PageHeader } from '@/components/ui/PageHeader';
import { Panel } from '@/components/ui/Panel';
import { StatTile } from '@/components/ui/StatTile';
import { ErrorState, InlineNotice, LoadingState } from '@/components/ui/States';
import { invalidateProduction } from '@/hooks/invalidate';
import { useMachines } from '@/hooks/queries';
import { useAuth } from '@/hooks/useAuth';
import { simulationApi } from '@/services/api';
import type { FaultScenario, SimulationResult } from '@/types/api';
import { describeError } from '@/utils/errors';
import { formatNumber, formatPercent, toApiDateTime } from '@/utils/format';

import { FaultScenarioBuilder } from './FaultScenarioBuilder';

function ResultSummary({ result }: { result: SimulationResult }) {
  const rate = result.inspections_created
    ? result.failed_inspections / result.inspections_created
    : 0;
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
      <StatTile label="Seed" value={String(result.seed)} />
      <StatTile label="Orders" value={formatNumber(result.orders_created)} />
      <StatTile label="Batches" value={formatNumber(result.batches_created)} />
      <StatTile label="Units" value={formatNumber(result.units_created)} />
      <StatTile label="Inspections" value={formatNumber(result.inspections_created)} />
      <StatTile
        label="Failed"
        value={formatNumber(result.failed_inspections)}
        detail={`defect rate ${formatPercent(rate)}`}
      />
      <StatTile label="Machine events" value={formatNumber(result.events_created)} />
      <StatTile label="Alerts" value={formatNumber(result.alerts_created)} />
    </div>
  );
}

export function SimulationPage() {
  const { can } = useAuth();
  const queryClient = useQueryClient();
  const machines = useMachines();
  const [seed, setSeed] = useState('42');
  const [startTime, setStartTime] = useState('2026-11-02T06:00');
  const [batchesPerMachine, setBatchesPerMachine] = useState('12');
  const [unitsPerBatch, setUnitsPerBatch] = useState('20');
  const [minutesPerBatch, setMinutesPerBatch] = useState('30');
  const [faults, setFaults] = useState<FaultScenario[]>([]);
  const [error, setError] = useState<string | null>(null);

  const run = useMutation({
    mutationFn: () =>
      simulationApi.run({
        seed: Number(seed),
        start_time: toApiDateTime(startTime),
        batches_per_machine: Number(batchesPerMachine),
        units_per_batch: Number(unitsPerBatch),
        minutes_per_batch: Number(minutesPerBatch),
        faults,
      }),
    onSuccess: () => {
      setError(null);
      invalidateProduction(queryClient);
    },
    onError: (cause) => setError(describeError(cause)),
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    run.mutate();
  }

  if (!can('simulation.run')) {
    return (
      <>
        <PageHeader title="Simulation" />
        <InlineNotice tone="info">
          Engineers and administrators can run simulations. Your role can browse the generated
          history on the other screens.
        </InlineNotice>
      </>
    );
  }

  return (
    <>
      <PageHeader
        title="Simulation"
        description="Generate a deterministic production history with optional fault scenarios. The run is written in one transaction."
      />
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1fr_380px]">
        <Panel title="Simulation request">
          {machines.isPending && <LoadingState label="Loading machines" />}
          {machines.isError && (
            <ErrorState error={machines.error} onRetry={() => void machines.refetch()} />
          )}
          <form onSubmit={handleSubmit} className="flex flex-col gap-4" aria-label="Run simulation">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
              <TextField
                label="Seed"
                type="number"
                min={0}
                value={seed}
                onChange={(e) => setSeed(e.target.value)}
                required
                hint="Same seed, same history."
              />
              <TextField
                label="Start time"
                type="datetime-local"
                value={startTime}
                onChange={(e) => setStartTime(e.target.value)}
                required
              />
              <TextField
                label="Batches per machine"
                type="number"
                min={1}
                max={200}
                value={batchesPerMachine}
                onChange={(e) => setBatchesPerMachine(e.target.value)}
                required
              />
              <TextField
                label="Units per batch"
                type="number"
                min={1}
                max={500}
                value={unitsPerBatch}
                onChange={(e) => setUnitsPerBatch(e.target.value)}
                required
              />
              <TextField
                label="Minutes per batch"
                type="number"
                min={1}
                max={600}
                value={minutesPerBatch}
                onChange={(e) => setMinutesPerBatch(e.target.value)}
                required
              />
            </div>
            <FaultScenarioBuilder
              machines={machines.data ?? []}
              faults={faults}
              onChange={setFaults}
            />
            {error && <InlineNotice tone="error">{error}</InlineNotice>}
            <div>
              <Button type="submit" variant="primary" busy={run.isPending}>
                Run simulation
              </Button>
            </div>
          </form>
        </Panel>
        <Panel title="Result" className="self-start">
          {run.data ? (
            <ResultSummary result={run.data} />
          ) : (
            <p className="text-sm text-ink-muted">
              The counts of created orders, batches, units, inspections, events, and alerts appear
              here after a run.
            </p>
          )}
        </Panel>
      </div>
    </>
  );
}
