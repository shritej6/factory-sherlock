import { titleCase } from '@/utils/format';
import { toneFor } from '@/utils/statusTone';
import type { Tone } from '@/utils/statusTone';

const TONE_CLASSES: Record<Tone, string> = {
  idle: 'border-status-idle bg-status-idle-soft text-status-idle',
  running: 'border-status-running bg-status-running-soft text-status-running',
  warning: 'border-status-warning bg-status-warning-soft text-status-warning',
  stopped: 'border-status-stopped bg-status-stopped-soft text-status-stopped',
  fault: 'border-status-fault bg-status-fault-soft text-status-fault',
  info: 'border-status-info bg-status-info-soft text-status-info',
};

/** A state lamp: a square indicator and the state word, outlined in the state colour. */
export function StatusBadge({ status, className = '' }: { status: string; className?: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 border px-1.5 py-px font-display text-xs font-semibold tracking-wide uppercase ${TONE_CLASSES[toneFor(status)]} ${className}`}
      data-status={status}
    >
      <span aria-hidden="true" className="inline-block h-1.5 w-1.5 bg-current" />
      {titleCase(status)}
    </span>
  );
}
