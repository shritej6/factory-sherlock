import { useState } from 'react';

import { ControlChart } from '@/components/charts/ControlChart';
import { SelectField } from '@/components/ui/Field';
import { SqlDisclosure } from '@/components/ui/SqlDisclosure';
import { EmptyState, ErrorState, LoadingState } from '@/components/ui/States';
import { useAnalyticsQuery, useMachines, useSpecifications } from '@/hooks/queries';
import type { QueryResult, SpecificationListItem } from '@/types/api';
import { describeControlChart, toControlChartSeries } from '@/utils/chartTransforms';
import { toApiDateTime } from '@/utils/format';

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
  const series = toControlChartSeries(result.rows);
  const target = Number(spec.target_value).toFixed(3);
  const tolerance = Number(spec.tolerance).toFixed(3);
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
        The grand mean and the control limits are computed over the subgroups in the selected
        window, so changing the window or the machine filter changes the limits.
      </p>
      <SqlDisclosure sql={result.sql} queryName={result.query} params={result.params} />
    </>
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
      {specifications.isPending && <LoadingState label="Loading specifications" />}
      {specifications.isError && (
        <div className="mt-3">
          <ErrorState error={specifications.error} onRetry={() => void specifications.refetch()} />
        </div>
      )}
      {specifications.data && specs.length === 0 && (
        <div className="mt-3">
          <EmptyState title="No specifications are defined" />
        </div>
      )}
      {selected && (
        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:max-w-xl">
          <SelectField
            label="Specification"
            value={String(selected.id)}
            onChange={(e) => setSpecificationId(e.target.value)}
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
            onChange={(e) => setMachineId(e.target.value)}
            hint="Optional"
          >
            <option value="">All machines</option>
            {machines.data?.map((machine) => (
              <option key={machine.id} value={machine.id}>
                {machine.code}
              </option>
            ))}
          </SelectField>
        </div>
      )}
      {selected && (
        <div className="mt-4">
          {result.isPending && <LoadingState label="Loading control chart" />}
          {result.isError && (
            <ErrorState error={result.error} onRetry={() => void result.refetch()} />
          )}
          {result.data && <ControlChartResult result={result.data} spec={selected} />}
        </div>
      )}
    </section>
  );
}
