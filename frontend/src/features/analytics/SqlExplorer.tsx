import { useState } from 'react';
import type { FormEvent } from 'react';

import { Button } from '@/components/ui/Button';
import { ResultRowsTable } from '@/components/ui/DataTable';
import { SelectField, TextField } from '@/components/ui/Field';
import { SqlDisclosure } from '@/components/ui/SqlDisclosure';
import { EmptyState, ErrorState, InlineNotice, LoadingState } from '@/components/ui/States';
import { useAnalyticsQuery, useMachines, useQueryCatalog } from '@/hooks/queries';
import type { QueryCatalogEntry, QueryParams } from '@/types/api';
import { formatNumber, toApiDateTime } from '@/utils/format';

import type { TimeWindow } from './WindowControls';
import { WindowControls } from './WindowControls';

interface SqlExplorerProps {
  defaultWindow: TimeWindow;
}

function readOnlyNote(name: string): string {
  if (name.startsWith('investigation.')) {
    return 'This query is run by the investigation engine when a case is opened; its rows appear on the case board.';
  }
  return 'This query needs a lot number or serial number and runs from the Material Traceability screen.';
}

export function SqlExplorer({ defaultWindow }: SqlExplorerProps) {
  const catalog = useQueryCatalog();
  const machines = useMachines();
  const [name, setName] = useState<string | null>(null);
  const [window, setWindow] = useState(defaultWindow);
  const [machineId, setMachineId] = useState('');
  const [threshold, setThreshold] = useState('0.10');
  const [hours, setHours] = useState('3');
  const [limit, setLimit] = useState('50');
  const [submitted, setSubmitted] = useState<{ name: string; params: QueryParams } | null>(null);
  const result = useAnalyticsQuery(
    submitted?.name ?? '',
    submitted?.params ?? {},
    submitted !== null,
  );

  const entries = catalog.data ?? [];
  const selected: QueryCatalogEntry | undefined =
    entries.find((entry) => entry.name === name) ?? entries.find((entry) => entry.runnable);
  const takes = (parameter: string) => selected?.parameters.includes(parameter) ?? false;

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected?.runnable) return;
    setSubmitted({
      name: selected.name,
      params: {
        ...(takes('window_start') ? { window_start: toApiDateTime(window.start) } : {}),
        ...(takes('window_end') ? { window_end: toApiDateTime(window.end) } : {}),
        ...(takes('machine_id') && machineId ? { machine_id: Number(machineId) } : {}),
        ...(takes('threshold') ? { threshold: Number(threshold) } : {}),
        ...(takes('hours') ? { hours: Number(hours) } : {}),
        ...(takes('limit') ? { limit: Number(limit) } : {}),
      },
    });
  }

  return (
    <section className="panel p-4" aria-label="SQL explorer">
      <h2 className="text-sm font-semibold text-ink">SQL Explorer</h2>
      <p className="mt-0.5 text-xs text-ink-muted">
        Every documented query in the database layer. Dashboard queries run here with your
        parameters; the others are shown for reading.
      </p>
      {catalog.isPending && <LoadingState label="Loading query catalog" />}
      {catalog.isError && (
        <div className="mt-3">
          <ErrorState error={catalog.error} onRetry={() => void catalog.refetch()} />
        </div>
      )}
      {catalog.data && catalog.data.length === 0 && (
        <div className="mt-3">
          <EmptyState title="The query catalog is empty" />
        </div>
      )}
      {selected && (
        <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-3">
          <SelectField
            label="Query"
            value={selected.name}
            onChange={(e) => setName(e.target.value)}
          >
            {entries.map((entry) => (
              <option key={entry.name} value={entry.name}>
                {entry.name}
                {entry.runnable ? '' : ' (read only)'}
              </option>
            ))}
          </SelectField>
          <p className="text-xs leading-relaxed text-ink-muted">{selected.description}</p>
          {selected.runnable ? (
            <>
              {(takes('window_start') || takes('window_end')) && (
                <WindowControls value={window} onChange={setWindow} />
              )}
              {selected.parameters.some((p) =>
                ['machine_id', 'threshold', 'hours', 'limit'].includes(p),
              ) && (
                <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                  {takes('machine_id') && (
                    <SelectField
                      label="Machine"
                      value={machineId}
                      onChange={(e) => setMachineId(e.target.value)}
                      hint="Optional"
                    >
                      <option value="">All machines</option>
                      {machines.data?.map((m) => (
                        <option key={m.id} value={m.id}>
                          {m.code}
                        </option>
                      ))}
                    </SelectField>
                  )}
                  {takes('threshold') && (
                    <TextField
                      label="Threshold"
                      type="number"
                      min={0}
                      max={1}
                      step="0.01"
                      value={threshold}
                      onChange={(e) => setThreshold(e.target.value)}
                      hint="Defect rate 0 to 1"
                    />
                  )}
                  {takes('hours') && (
                    <TextField
                      label="Hours"
                      type="number"
                      min={1}
                      max={72}
                      value={hours}
                      onChange={(e) => setHours(e.target.value)}
                      hint="Before and after events"
                    />
                  )}
                  {takes('limit') && (
                    <TextField
                      label="Limit"
                      type="number"
                      min={1}
                      max={500}
                      value={limit}
                      onChange={(e) => setLimit(e.target.value)}
                    />
                  )}
                </div>
              )}
              {selected.parameters.length === 0 && (
                <p className="text-xs text-ink-faint">This query takes no parameters.</p>
              )}
              <div>
                <Button type="submit" variant="primary" busy={result.isFetching}>
                  Run query
                </Button>
              </div>
            </>
          ) : (
            <>
              <InlineNotice tone="info">{readOnlyNote(selected.name)}</InlineNotice>
              <SqlDisclosure sql={selected.sql} queryName={selected.name} />
            </>
          )}
        </form>
      )}
      {selected?.runnable && (
        <div className="mt-4">
          {submitted === null && (
            <EmptyState
              title="Choose a query and run it"
              hint="Rows and the executed SQL appear here."
            />
          )}
          {submitted !== null && result.isPending && <LoadingState label="Running query" />}
          {result.isError && (
            <ErrorState error={result.error} onRetry={() => void result.refetch()} />
          )}
          {result.data && (
            <>
              <p role="status" className="mb-2 text-xs text-ink-muted">
                <code className="font-mono text-ink">{result.data.query}</code> returned{' '}
                {formatNumber(result.data.rows.length)} row(s).
              </p>
              <ResultRowsTable
                rows={result.data.rows}
                caption={`Rows returned by ${result.data.query}`}
              />
              <SqlDisclosure
                sql={result.data.sql}
                queryName={result.data.query}
                params={result.data.params}
              />
            </>
          )}
        </div>
      )}
    </section>
  );
}
