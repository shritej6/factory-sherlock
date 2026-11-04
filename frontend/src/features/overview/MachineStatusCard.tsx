import { Link } from 'react-router';

import { StatusBadge } from '@/components/ui/StatusBadge';
import { toneFor } from '@/utils/statusTone';
import type { Machine } from '@/types/api';
import { formatDateTime } from '@/utils/format';

const EDGE_CLASSES: Record<ReturnType<typeof toneFor>, string> = {
  idle: 'border-l-status-idle',
  running: 'border-l-status-running',
  warning: 'border-l-status-warning',
  stopped: 'border-l-status-stopped',
  fault: 'border-l-status-fault',
  info: 'border-l-status-info',
};

export function MachineStatusCard({ machine }: { machine: Machine }) {
  return (
    <Link
      to={`/machines?machine=${machine.id}`}
      className={`panel block border-l-4 px-4 py-3 hover:bg-surface-muted ${EDGE_CLASSES[toneFor(machine.status)]}`}
      data-testid="machine-card"
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="font-mono text-sm font-semibold text-ink">{machine.code}</p>
          <p className="text-xs text-ink-muted">{machine.name}</p>
        </div>
        <StatusBadge status={machine.status} />
      </div>
      <p className="mt-2 text-xs text-ink-faint">Updated {formatDateTime(machine.updated_at)}</p>
    </Link>
  );
}
