import { PageBody, Pagination } from '@/components/ui/Pagination';
import { Panel } from '@/components/ui/Panel';
import { ErrorState, LoadingState } from '@/components/ui/States';
import { useMachineEvents } from '@/hooks/queries';
import { usePageState } from '@/hooks/usePageState';
import type { Machine } from '@/types/api';

import { EventTimeline } from './EventTimeline';

/** Mount with key={machine.id} so the page resets when another machine is selected. */
export function MachineEventsPanel({ machine }: { machine: Machine }) {
  const { page, setPage } = usePageState();
  const events = useMachineEvents(machine.id, page);
  return (
    <Panel title="Event timeline" description={`${machine.code} · most recent first`}>
      {events.isPending && <LoadingState label="Loading events" />}
      {events.isError && <ErrorState error={events.error} onRetry={() => void events.refetch()} />}
      {events.data && (
        <>
          <PageBody loading={events.isPlaceholderData}>
            <EventTimeline events={events.data.items} />
          </PageBody>
          <Pagination
            total={events.data.total}
            limit={page.limit}
            offset={page.offset}
            onChange={setPage}
            label="Machine events"
            className="mt-3"
          />
        </>
      )}
    </Panel>
  );
}
