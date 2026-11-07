import { Link } from 'react-router';

import { StatusBadge } from '@/components/ui/StatusBadge';
import { EmptyState } from '@/components/ui/States';
import type { InvestigationBatchLink, ProductionBatch } from '@/types/api';
import { formatPercent } from '@/utils/format';

interface FlaggedBatchesProps {
  links: InvestigationBatchLink[];
  batches: ProductionBatch[] | undefined;
  /** Defect rates from rule R5, keyed by batch id, when available. */
  rates: Map<number, number>;
  canQuarantine: boolean;
}

export function FlaggedBatches({ links, batches, rates, canQuarantine }: FlaggedBatchesProps) {
  if (links.length === 0) return <EmptyState title="No batches exceeded the review threshold" />;
  return (
    <ul className="divide-y divide-border" aria-label="Flagged batches">
      {links.map((link) => {
        const batch = batches?.find((b) => b.id === link.batch_id);
        const rate = rates.get(link.batch_id);
        const batchName = batch?.batch_number ?? `Batch ${link.batch_id}`;
        const linkText =
          canQuarantine && batch?.status !== 'QUARANTINED' ? 'Review and quarantine' : 'View batch';
        return (
          <li
            key={link.batch_id}
            className="flex flex-wrap items-center justify-between gap-2 py-2"
          >
            <div>
              <p className="font-mono text-sm font-medium text-ink">{batchName}</p>
              <p className="text-xs text-ink-muted">
                {link.reason}
                {rate !== undefined && ` · defect rate ${formatPercent(rate)}`}
              </p>
            </div>
            <div className="flex items-center gap-2">
              {batch && <StatusBadge status={batch.status} />}
              <Link
                to={`/batches?batch=${link.batch_id}${batch ? `&machine=${batch.machine_id}` : ''}`}
                className="text-xs text-accent hover:underline"
                aria-label={`${linkText} ${batchName}`}
              >
                {linkText}
              </Link>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
