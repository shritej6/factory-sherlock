import { Link } from 'react-router';

import { Button } from '@/components/ui/Button';
import { PageHeader } from '@/components/ui/PageHeader';
import { PageBody, Pagination } from '@/components/ui/Pagination';
import { Panel } from '@/components/ui/Panel';
import { StatTile } from '@/components/ui/StatTile';
import { EmptyState, ErrorState, InlineNotice, LoadingState } from '@/components/ui/States';
import {
  LOOKUP_PAGE,
  useAlerts,
  useCheckOverdueOrders,
  useInvestigations,
  useMachines,
  useOrderCounts,
  useQualitySummary,
} from '@/hooks/queries';
import { useAuth } from '@/hooks/useAuth';
import { usePageState } from '@/hooks/usePageState';
import type { OverdueCheckResponse } from '@/types/api';
import { describeError } from '@/utils/errors';
import { formatNumber, formatPercent } from '@/utils/format';

import { AlertsList } from './AlertsList';
import { MachineStatusCard } from './MachineStatusCard';

/**
 * The Overview is the only screen that lists alerts, so it pages through all of them
 * rather than showing a fixed number of recent ones; a short page keeps the panel compact.
 */
const ALERT_PAGE_SIZE = 10;
const ALERT_PAGE_SIZES: readonly number[] = [10, 25, 50];

const plural = (count: number, noun: string) => `${count} ${noun}${count === 1 ? '' : 's'}`;

/** One sentence for the notice shown after the overdue order check completes. */
function describeOverdueCheck({ checked, raised }: OverdueCheckResponse): string {
  const orders = `Checked ${plural(checked, 'open order')}`;
  return raised === 0
    ? `${orders}, no new overdue alerts`
    : `${orders}, raised ${plural(raised, 'overdue alert')}`;
}

export function OverviewPage() {
  const { can } = useAuth();
  const machines = useMachines();
  const summary = useQualitySummary();
  const orderCounts = useOrderCounts(['RELEASED', 'IN_PROGRESS']);
  const { page: alertPage, setPage: setAlertPage } = usePageState(ALERT_PAGE_SIZE);
  const alerts = useAlerts(alertPage);
  const overdueCheck = useCheckOverdueOrders();
  const investigations = useInvestigations(LOOKUP_PAGE);

  const activeOrders = orderCounts.data
    ? orderCounts.data.RELEASED + orderCounts.data.IN_PROGRESS
    : undefined;
  const openInvestigations = investigations.data?.items.filter((i) => i.status !== 'CLOSED').length;

  return (
    <>
      <PageHeader
        title="Factory Overview"
        description="Live machine states, fleet quality, and the alerts that need attention."
      />
      <section aria-label="Machine status" className="mb-5">
        {machines.isPending && <LoadingState label="Loading machines" />}
        {machines.isError && (
          <ErrorState error={machines.error} onRetry={() => void machines.refetch()} />
        )}
        {machines.data && machines.data.length === 0 && (
          <EmptyState
            title="No machines registered"
            hint="Run a simulation to create machines and production history."
          />
        )}
        {machines.data && machines.data.length > 0 && (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {machines.data.map((machine) => (
              <MachineStatusCard key={machine.id} machine={machine} />
            ))}
          </div>
        )}
      </section>

      <section aria-label="Quality summary" className="mb-5">
        {summary.isError && (
          <ErrorState error={summary.error} onRetry={() => void summary.refetch()} />
        )}
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4 xl:grid-cols-6">
          <StatTile
            label="Units produced"
            value={summary.data ? formatNumber(summary.data.total_produced) : '...'}
          />
          <StatTile
            label="Inspections"
            value={summary.data ? formatNumber(summary.data.total_inspected) : '...'}
          />
          <StatTile
            label="Passed"
            value={summary.data ? formatNumber(summary.data.passed) : '...'}
          />
          <StatTile
            label="Failed"
            value={summary.data ? formatNumber(summary.data.failed) : '...'}
          />
          <StatTile
            label="Defect rate"
            value={summary.data ? formatPercent(summary.data.defect_rate) : '...'}
            detail="failed / inspected"
          />
          <StatTile
            label="Active orders"
            value={activeOrders === undefined ? '...' : formatNumber(activeOrders)}
            detail="released or in progress"
          />
        </div>
      </section>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <Panel
          title="Recent alerts"
          className="xl:col-span-2"
          actions={
            <>
              {can('alert.acknowledge') && (
                <Button
                  size="sm"
                  busy={overdueCheck.isPending}
                  onClick={() => overdueCheck.mutate()}
                >
                  Check overdue orders
                </Button>
              )}
              <Link to="/analytics" className="text-xs text-accent hover:underline">
                Analytics
              </Link>
            </>
          }
        >
          {(overdueCheck.isSuccess || overdueCheck.isError) && (
            <div className="mb-3">
              {overdueCheck.isSuccess && (
                <InlineNotice tone="success">
                  {describeOverdueCheck(overdueCheck.data)}
                </InlineNotice>
              )}
              {overdueCheck.isError && (
                <InlineNotice tone="error">{describeError(overdueCheck.error)}</InlineNotice>
              )}
            </div>
          )}
          {alerts.isPending && <LoadingState label="Loading alerts" />}
          {alerts.isError && (
            <ErrorState error={alerts.error} onRetry={() => void alerts.refetch()} />
          )}
          {alerts.data && (
            <>
              <PageBody loading={alerts.isPlaceholderData}>
                <AlertsList alerts={alerts.data.items} />
              </PageBody>
              <Pagination
                total={alerts.data.total}
                limit={alertPage.limit}
                offset={alertPage.offset}
                onChange={setAlertPage}
                label="Alerts"
                pageSizes={ALERT_PAGE_SIZES}
                className="mt-3"
              />
            </>
          )}
        </Panel>
        <Panel
          title="Investigations"
          actions={
            <Link to="/investigations" className="text-xs text-accent hover:underline">
              Open case list
            </Link>
          }
        >
          {investigations.isPending && <LoadingState label="Loading investigations" />}
          {investigations.isError && (
            <ErrorState
              error={investigations.error}
              onRetry={() => void investigations.refetch()}
            />
          )}
          {investigations.data && (
            <div className="flex flex-col gap-3">
              <p className="text-3xl font-semibold text-ink">
                {formatNumber(openInvestigations ?? 0)}
                <span className="ml-2 text-sm font-normal text-ink-muted">open or in review</span>
              </p>
              {investigations.data.items.length === 0 ? (
                <EmptyState
                  title="No investigations yet"
                  hint="Open one from the Investigations screen."
                />
              ) : (
                <ul className="divide-y divide-border text-sm">
                  {investigations.data.items.slice(0, 5).map((inv) => (
                    <li key={inv.id} className="py-2">
                      <Link
                        to={`/investigations/${inv.id}`}
                        className="text-accent hover:underline"
                      >
                        {inv.title}
                      </Link>
                      <p className="text-xs text-ink-muted">
                        {inv.status.replace('_', ' ')} · {inv.batch_links.length} flagged batch(es)
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </Panel>
      </div>
    </>
  );
}
