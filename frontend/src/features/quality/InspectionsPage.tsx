import { useState } from 'react';

import { DefectRateChart } from '@/components/charts/DefectRateChart';
import { Chip } from '@/components/ui/Chip';
import type { Column } from '@/components/ui/DataTable';
import { DataTable } from '@/components/ui/DataTable';
import { Disclosure } from '@/components/ui/Disclosure';
import { SelectField, TextField } from '@/components/ui/Field';
import { PageHeader } from '@/components/ui/PageHeader';
import { PageBody, Pagination } from '@/components/ui/Pagination';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { ErrorState, LoadingState } from '@/components/ui/States';
import { useAnalyticsQuery, useInspections } from '@/hooks/queries';
import { useAuth } from '@/hooks/useAuth';
import { usePageState } from '@/hooks/usePageState';
import type { Inspection, InspectionResult } from '@/types/api';
import { DEFAULT_WINDOW_END, DEFAULT_WINDOW_START } from '@/types/constants';
import { toDefectRateSeries } from '@/utils/chartTransforms';
import { formatDateTime, toApiDateTime } from '@/utils/format';

import { ImportInspectionsPanel } from './ImportInspectionsPanel';
import { InspectionForm } from './InspectionForm';

export function InspectionsPage() {
  const { can } = useAuth();
  const [result, setResult] = useState<InspectionResult | ''>('');
  const [batchId, setBatchId] = useState('');
  const { page, setPage, resetOffset } = usePageState();
  const inspections = useInspections({
    result,
    ...(batchId ? { batch_id: Number(batchId) } : {}),
    ...page,
  });
  const defectRates = useAnalyticsQuery('machine_defect_rate_comparison', {
    window_start: toApiDateTime(DEFAULT_WINDOW_START),
    window_end: toApiDateTime(DEFAULT_WINDOW_END),
  });

  const columns: Column<Inspection>[] = [
    { key: 'id', header: 'Id', align: 'right', render: (i) => i.id },
    { key: 'unit_id', header: 'Unit', align: 'right', render: (i) => i.unit_id },
    { key: 'specification_id', header: 'Spec', align: 'right', render: (i) => i.specification_id },
    {
      key: 'measured_value',
      header: 'Measured',
      align: 'right',
      render: (i) => <span className="font-mono">{i.measured_value}</span>,
    },
    { key: 'result', header: 'Result', render: (i) => <StatusBadge status={i.result} /> },
    {
      key: 'defect_codes',
      header: 'Defect codes',
      render: (i) => (
        <span className="flex flex-wrap gap-1">
          {i.defect_codes.map((code) => (
            <Chip key={code}>{code}</Chip>
          ))}
        </span>
      ),
    },
    { key: 'inspected_at', header: 'Inspected', render: (i) => formatDateTime(i.inspected_at) },
  ];

  return (
    <>
      <PageHeader
        title="Quality Inspection"
        description="Measurements are compared against product specifications; failures carry defect codes."
        actions={
          can('inspection.record') && (
            <Disclosure label="Record inspection">
              {(close) => <InspectionForm onDone={close} />}
            </Disclosure>
          )
        }
      />
      <ImportInspectionsPanel />
      <div className="mb-4">
        {defectRates.isError && (
          <ErrorState error={defectRates.error} onRetry={() => void defectRates.refetch()} />
        )}
        {defectRates.isPending && <LoadingState label="Loading defect rates" />}
        {defectRates.data && <DefectRateChart points={toDefectRateSeries(defectRates.data.rows)} />}
      </div>
      <div className="mb-3 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:max-w-xl">
        <SelectField
          label="Result"
          value={result}
          onChange={(e) => {
            setResult(e.target.value as InspectionResult | '');
            resetOffset();
          }}
        >
          <option value="">All results</option>
          <option value="PASS">Pass</option>
          <option value="FAIL">Fail</option>
        </SelectField>
        <TextField
          label="Batch id"
          type="number"
          min={1}
          value={batchId}
          onChange={(e) => {
            setBatchId(e.target.value);
            resetOffset();
          }}
          placeholder="Any batch"
        />
      </div>
      <div className="panel">
        {inspections.isPending && <LoadingState label="Loading inspections" />}
        {inspections.isError && (
          <div className="p-4">
            <ErrorState error={inspections.error} onRetry={() => void inspections.refetch()} />
          </div>
        )}
        {inspections.data && (
          <>
            <PageBody loading={inspections.isPlaceholderData}>
              <DataTable
                columns={columns}
                rows={inspections.data.items}
                rowKey={(i) => i.id}
                caption="Inspections"
                emptyTitle="No inspections match these filters"
              />
            </PageBody>
            <Pagination
              total={inspections.data.total}
              limit={page.limit}
              offset={page.offset}
              onChange={setPage}
              label="Inspections"
              className="px-4"
            />
          </>
        )}
      </div>
    </>
  );
}
