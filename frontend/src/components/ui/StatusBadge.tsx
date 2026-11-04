import { titleCase } from '@/utils/format';
import { toneFor } from '@/utils/statusTone';
import type { Tone } from '@/utils/statusTone';

const TONE_CLASSES: Record<Tone, string> = {
  idle: 'bg-status-idle-soft text-status-idle',
  running: 'bg-status-running-soft text-status-running',
  warning: 'bg-status-warning-soft text-status-warning',
  stopped: 'bg-status-stopped-soft text-status-stopped',
  fault: 'bg-status-fault-soft text-status-fault',
  info: 'bg-status-info-soft text-status-info',
};

export function StatusBadge({ status, className = '' }: { status: string; className?: string }) {
  return (
    <span
      className={`inline-flex items-center rounded-sm px-1.5 py-0.5 text-[11px] font-semibold tracking-wide uppercase ${TONE_CLASSES[toneFor(status)]} ${className}`}
      data-status={status}
    >
      {titleCase(status)}
    </span>
  );
}
