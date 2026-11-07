import { useState } from 'react';
import type { ChangeEvent, FormEvent } from 'react';

import { Button } from '@/components/ui/Button';
import type { Column } from '@/components/ui/DataTable';
import { DataTable } from '@/components/ui/DataTable';
import { Disclosure } from '@/components/ui/Disclosure';
import { TextField } from '@/components/ui/Field';
import { InlineNotice } from '@/components/ui/States';
import { useAuth } from '@/hooks/useAuth';
import { ApiError } from '@/services/http';
import type { InspectionImportResult, InspectionImportRowError } from '@/types/api';
import { describeError, extractImportRowErrors } from '@/utils/errors';

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

function ImportForm() {
  const importInspections = useImportInspections();
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | undefined>();
  // Remounting the input is the only way to clear a native file field after a successful import.
  const [inputKey, setInputKey] = useState(0);

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const chosen = event.target.files?.[0] ?? null;
    importInspections.reset();
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

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) return;
    importInspections.mutate(file, {
      onSuccess: () => {
        setFile(null);
        setInputKey((key) => key + 1);
      },
    });
  }

  const rowErrors =
    importInspections.error instanceof ApiError
      ? extractImportRowErrors(importInspections.error)
      : [];

  return (
    <form
      onSubmit={handleSubmit}
      className="panel mt-3 flex flex-col gap-3 p-4"
      aria-label="Import inspections from CSV"
    >
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
          UTF-8 CSV with a header row, at most {MAX_IMPORT_ROWS} data rows and 1 MiB. Nothing is
          imported if any row fails validation.
        </p>
      </div>
      <TextField
        key={inputKey}
        label="CSV file"
        type="file"
        accept=".csv,text/csv"
        onChange={handleFileChange}
        error={fileError}
        className="max-w-md"
      />
      {importInspections.data && (
        <InlineNotice tone="success">{summarize(importInspections.data)}</InlineNotice>
      )}
      {importInspections.error && (
        <InlineNotice tone="error">
          {rowErrors.length > 0
            ? `${importInspections.error.message}. Fix the rows below and import the file again.`
            : describeError(importInspections.error)}
        </InlineNotice>
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
      <div>
        <Button type="submit" variant="primary" disabled={!file} busy={importInspections.isPending}>
          Import
        </Button>
      </div>
    </form>
  );
}
