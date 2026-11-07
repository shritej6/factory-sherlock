import type { UseQueryResult } from '@tanstack/react-query';
import { useMemo, useState } from 'react';

import { ControlChart } from '@/components/charts/ControlChart';
import { SelectField } from '@/components/ui/Field';
import { SqlDisclosure } from '@/components/ui/SqlDisclosure';
import { EmptyState, ErrorNotice, ErrorState, LoadingState } from '@/components/ui/States';
import { useAnalyticsQuery, useMachines, useSpecifications } from '@/hooks/queries';
import type { Machine, QueryResult, SpecificationListItem } from '@/types/api';
import { describeControlChart, toControlChartSeries } from '@/utils/chartTransforms';
import { describeError } from '@/utils/errors';
import { formatMeasure, toApiDateTime } from '@/utils/format';

import type { TimeWindow } from './WindowControls';

export const CONTROL_CHART_QUERY = 'characteristic_control_chart';

interface ControlChartPanelProps {
  /** The page's time window; the panel adds no date range of its own. */
  window: TimeWindow;
}

function specificationLabel(spec: SpecificationListItem): string {
  return `${spec.product_code} ${spec.characteristic} (${spec.unit})`;
}

function ControlChartResult({
  result,
  spec,
}: {
  result: QueryResult;
  spec: SpecificationListItem;
}) {
  const series = useMemo(() => toControlChartSeries(result.rows), [result.rows]);
  const target = formatMeasure(spec.target_value);
  const tolerance = formatMeasure(spec.tolerance);
  return (
    <>
      <ControlChart
        series={series}
        unit={spec.unit}
        title={`X-bar chart: ${specificationLabel(spec)}`}
        description={`Mean measured value per production batch. Target ${target} ${spec.unit}, tolerance ${tolerance} ${spec.unit}.`}
      />
      <p className="mt-3 text-sm text-ink">{describeControlChart(series)}</p>
      <p className="mt-1 text-xs text-ink-muted">
        The grand mean and the pooled standard deviation are computed over the subgroups in the
        selected window, so changing the window or the machine filter changes the limits. Each
        subgroup has its own limits, three pooled standard deviations divided by the square root of
        its sample count either side of the grand mean, so small subgroups get wider limits.
      </p>
      <SqlDisclosure sql={result.sql} queryName={result.query} params={result.params} />
    </>
  );
}

interface ChartFiltersProps {
  specs: SpecificationListItem[];
  selected: SpecificationListItem;
  onSpecificationChange: (id: string) => void;
  machines: UseQueryResult<Machine[]>;
  machineId: string;
  onMachineChange: (id: string) => void;
}

/** Inline failure for the machine list; the chart still renders for all machines. */
function MachinesNotice({ machines }: { machines: UseQueryResult<Machine[]> }) {
  if (!machines.isError) return null;
  return (
    <div className="sm:col-span-2">
      <ErrorNotice error={machines.error}>
        The machine list could not be loaded, so the chart cannot be filtered by machine:{' '}
        {describeError(machines.error)}
      </ErrorNotice>
    </div>
  );
}

function ChartFilters({
  specs,
  selected,
  onSpecificationChange,
  machines,
  machineId,
  onMachineChange,
}: ChartFiltersProps) {
  return (
    <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:max-w-xl">
      <SelectField
        label="Specification"
        value={String(selected.id)}
        onChange={(e) => onSpecificationChange(e.target.value)}
      >
        {specs.map((spec) => (
          <option key={spec.id} value={spec.id}>
            {specificationLabel(spec)}
          </option>
        ))}
      </SelectField>
      <SelectField
        label="Machine"
        value={machineId}
        onChange={(e) => onMachineChange(e.target.value)}
        hint="Optional"
      >
        <option value="">All machines</option>
        {machines.data?.map((machine) => (
          <option key={machine.id} value={machine.id}>
            {machine.code}
          </option>
        ))}
      </SelectField>
      <MachinesNotice machines={machines} />
    </div>
  );
}

/** Loading, failure, and empty notices for the specification list that drives the panel. */
function SpecificationStatus({
  specifications,
}: {
  specifications: UseQueryResult<SpecificationListItem[]>;
}) {
  if (specifications.isPending) return <LoadingState label="Loading specifications" />;
  if (specifications.isError) {
    return (
      <div className="mt-3">
        <ErrorState error={specifications.error} onRetry={() => void specifications.refetch()} />
      </div>
    );
  }
  if (specifications.data.length === 0) {
    return (
      <div className="mt-3">
        <EmptyState title="No specifications are defined" />
      </div>
    );
  }
  return null;
}

function ChartOutcome({
  result,
  spec,
}: {
  result: UseQueryResult<QueryResult>;
  spec: SpecificationListItem;
}) {
  return (
    <div className="mt-4">
      {result.isPending && <LoadingState label="Loading control chart" />}
      {result.isError && <ErrorState error={result.error} onRetry={() => void result.refetch()} />}
      {result.data && <ControlChartResult result={result.data} spec={spec} />}
    </div>
  );
}

export function ControlChartPanel({ window }: ControlChartPanelProps) {
  const specifications = useSpecifications();
  const machines = useMachines();
  const [specificationId, setSpecificationId] = useState('');
  const [machineId, setMachineId] = useState('');
  const specs = specifications.data ?? [];
  const selected = specs.find((spec) => String(spec.id) === specificationId) ?? specs[0];
  const result = useAnalyticsQuery(
    CONTROL_CHART_QUERY,
    {
      specification_id: selected?.id,
      window_start: toApiDateTime(window.start),
      window_end: toApiDateTime(window.end),
      ...(machineId ? { machine_id: Number(machineId) } : {}),
    },
    selected !== undefined,
  );

  return (
    <section className="panel mb-4 p-4" aria-label="Control chart">
      <h2 className="text-sm font-semibold text-ink">Control chart</h2>
      <p className="mt-0.5 text-xs text-ink-muted">
        Batch means of one measured characteristic against three-sigma control limits and the
        specification limits, for the window above.
      </p>
      <SpecificationStatus specifications={specifications} />
      {selected && (
        <ChartFilters
          specs={specs}
          selected={selected}
          onSpecificationChange={setSpecificationId}
          machines={machines}
          machineId={machineId}
          onMachineChange={setMachineId}
        />
      )}
      {selected && <ChartOutcome result={result} spec={selected} />}
    </section>
  );
}
