import { useState } from 'react';
import type { ChangeEvent, FormEvent } from 'react';

import { Button } from '@/components/ui/Button';
import type { Column } from '@/components/ui/DataTable';
import { DataTable } from '@/components/ui/DataTable';
import { Disclosure } from '@/components/ui/Disclosure';
import { TextField } from '@/components/ui/Field';
import { ErrorNotice, InlineNotice } from '@/components/ui/States';
import { useAuth } from '@/hooks/useAuth';
import { ApiError } from '@/services/http';
import type { InspectionImportResult, InspectionImportRowError } from '@/types/api';
import { extractImportRowErrors } from '@/utils/errors';
import { formatNumber } from '@/utils/format';

import { useImportInspections } from './useImportInspections';

export const MAX_IMPORT_BYTES = 1024 * 1024;
export const MAX_IMPORT_ROWS = 5000;

const COLUMNS = [
  { name: 'serial_number', note: 'required' },
  { name: 'characteristic', note: 'required' },
  { name: 'measured_value', note: 'required' },
  { name: 'inspected_at', note: 'optional, ISO 8601' },
  { name: 'defect_type_codes', note: 'optional, separated by |' },
];

const ERROR_COLUMNS: Column<InspectionImportRowError>[] = [
  { key: 'row', header: 'Row', align: 'right', render: (e) => e.row },
  {
    key: 'field',
    header: 'Field',
    render: (e) =>
      e.field ? (
        <span className="font-mono">{e.field}</span>
      ) : (
        <span className="text-ink-muted">whole row</span>
      ),
  },
  { key: 'message', header: 'Message', render: (e) => e.message },
];

function formatMiB(bytes: number): string {
  return `${(bytes / MAX_IMPORT_BYTES).toFixed(1)} MiB`;
}

function pluralize(count: number, noun: string): string {
  return `${count} ${count === 1 ? noun : `${noun}s`}`;
}

function summarize(result: InspectionImportResult): string {
  return `Imported ${pluralize(result.imported, 'inspection')}, ${result.failed_inspections} failed the specification.`;
}

/** Collapsed CSV upload for operators and engineers; viewers get nothing, like the manual form. */
export function ImportInspectionsPanel() {
  const { can } = useAuth();
  if (!can('inspection.record')) return null;
  return (
    <div className="mb-4 flex flex-wrap gap-3">
      <Disclosure label="Import inspections from CSV" closeLabel="Hide import" variant="secondary">
        {() => <ImportForm />}
      </Disclosure>
    </div>
  );
}

/** The chosen file, its size check, and the key that remounts the native input to clear it. */
function useCsvFile() {
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | undefined>();
  const [inputKey, setInputKey] = useState(0);

  function choose(chosen: File | null) {
    if (chosen && chosen.size > MAX_IMPORT_BYTES) {
      setFile(null);
      setFileError(
        `${chosen.name} is ${formatMiB(chosen.size)}; the limit is 1 MiB. Split the file and import each part.`,
      );
      return;
    }
    setFileError(undefined);
    setFile(chosen);
  }

  function clear() {
    setFile(null);
    setInputKey((key) => key + 1);
  }

  return { file, fileError, inputKey, choose, clear };
}

function ImportInstructions() {
  return (
    <div className="text-xs text-ink-muted">
      <p className="font-medium text-ink">Expected columns</p>
      <ul className="mt-1 flex flex-wrap gap-x-4 gap-y-1">
        {COLUMNS.map((column) => (
          <li key={column.name}>
            <code className="font-mono text-ink">{column.name}</code> ({column.note})
          </li>
        ))}
      </ul>
      <p className="mt-2">
        UTF-8 CSV with a header row, at most {formatNumber(MAX_IMPORT_ROWS)} data rows and 1 MiB.
        Nothing is imported if any row fails validation.
      </p>
    </div>
  );
}

/** The success summary, or the failure notice with the per-row errors from a 422. */
function ImportOutcome({ result, error }: { result?: InspectionImportResult; error: unknown }) {
  const rowErrors = error instanceof ApiError ? extractImportRowErrors(error) : [];
  return (
    <>
      {result && <InlineNotice tone="success">{summarize(result)}</InlineNotice>}
      {error instanceof Error && (
        <ErrorNotice error={error}>
          {rowErrors.length > 0
            ? `${error.message}. Fix the rows below and import the file again.`
            : undefined}
        </ErrorNotice>
      )}
      {rowErrors.length > 0 && (
        <DataTable
          columns={ERROR_COLUMNS}
          rows={rowErrors}
          rowKey={(_, index) => index}
          caption="Import errors by row"
          dense
        />
      )}
    </>
  );
}

function ImportButton({ disabled, busy }: { disabled: boolean; busy: boolean }) {
  return (
    <div>
      <Button type="submit" variant="primary" disabled={disabled} busy={busy}>
        Import
      </Button>
    </div>
  );
}

function ImportForm() {
  const importInspections = useImportInspections();
  const csv = useCsvFile();

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    importInspections.reset();
    csv.choose(event.target.files?.[0] ?? null);
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!csv.file) return;
    importInspections.mutate(csv.file, { onSuccess: csv.clear });
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="panel mt-3 flex flex-col gap-3 p-4"
      aria-label="Import inspections from CSV"
    >
      <ImportInstructions />
      <TextField
        key={csv.inputKey}
        label="CSV file"
        type="file"
        accept=".csv,text/csv"
        onChange={handleFileChange}
        error={csv.fileError}
        className="max-w-md"
      />
      <ImportOutcome result={importInspections.data} error={importInspections.error} />
      <ImportButton disabled={!csv.file} busy={importInspections.isPending} />
    </form>
  );
}
