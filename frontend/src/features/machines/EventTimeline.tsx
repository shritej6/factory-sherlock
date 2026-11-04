import { StatusBadge } from '@/components/ui/StatusBadge';
import { EmptyState } from '@/components/ui/States';
import type { MachineEvent } from '@/types/api';
import { formatDateTime, titleCase } from '@/utils/format';

export function EventTimeline({ events }: { events: MachineEvent[] }) {
  if (events.length === 0) return <EmptyState title="No events recorded for this machine" />;
  return (
    <ol
      className="relative flex flex-col gap-0 border-l border-border pl-4"
      aria-label="Machine events"
    >
      {events.map((event) => (
        <li key={event.id} className="relative pb-4 last:pb-0">
          <span
            aria-hidden="true"
            className="absolute top-1.5 -left-[21px] h-2.5 w-2.5 rounded-full border-2 border-surface bg-ink-faint"
          />
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-xs text-ink-muted">
              {formatDateTime(event.occurred_at)}
            </span>
            <span className="text-sm font-medium text-ink">{titleCase(event.event_type)}</span>
            <StatusBadge status={event.severity} />
          </div>
          {event.previous_state && event.new_state && (
            <p className="mt-0.5 text-xs text-ink-muted">
              {titleCase(event.previous_state)} to {titleCase(event.new_state)}
            </p>
          )}
          <p className="mt-0.5 text-sm text-ink-muted">{event.description}</p>
        </li>
      ))}
    </ol>
  );
}
