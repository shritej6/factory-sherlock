import type { ReactNode } from 'react';

import type { ResultRow } from '@/types/api';
import { humanizeKey } from '@/utils/format';
import { renderCell } from '@/utils/renderCell';

import { EmptyState } from './States';

export interface Column<T> {
  key: string;
  header: string;
  render?: (row: T) => ReactNode;
  align?: 'left' | 'right';
}

interface DataTableProps<T> {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T, index: number) => string | number;
  caption: string;
  emptyTitle?: string;
  emptyHint?: string;
  dense?: boolean;
}

export function DataTable<T extends object>({
  columns,
  rows,
  rowKey,
  caption,
  emptyTitle = 'No rows',
  emptyHint,
  dense = false,
}: DataTableProps<T>) {
  if (rows.length === 0) return <EmptyState title={emptyTitle} hint={emptyHint} />;
  return (
    <div className="overflow-x-auto">
      <table className={`data-table ${dense ? 'text-xs' : ''}`}>
        <caption className="sr-only">{caption}</caption>
        <thead>
          <tr>
            {columns.map((column) => (
              <th
                key={column.key}
                scope="col"
                className={column.align === 'right' ? 'text-right' : ''}
              >
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={rowKey(row, index)}>
              {columns.map((column) => (
                <td key={column.key} className={column.align === 'right' ? 'text-right' : ''}>
                  {column.render ? column.render(row) : renderCell((row as ResultRow)[column.key])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Renders rows returned by SQL queries without knowing their columns ahead of time. */
export function ResultRowsTable({
  rows,
  caption,
  emptyTitle = 'The query returned no rows',
}: {
  rows: ResultRow[];
  caption: string;
  emptyTitle?: string;
}) {
  const keys = rows.length > 0 ? Object.keys(rows[0]) : [];
  const columns: Column<ResultRow>[] = keys.map((key) => ({
    key,
    header: humanizeKey(key),
    align: typeof rows[0][key] === 'number' ? 'right' : 'left',
    render: (row) => renderCell(row[key], key),
  }));
  return (
    <DataTable
      columns={columns}
      rows={rows}
      rowKey={(_, index) => index}
      caption={caption}
      emptyTitle={emptyTitle}
      dense
    />
  );
}
