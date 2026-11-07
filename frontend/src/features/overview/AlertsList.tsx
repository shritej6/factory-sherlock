import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { Link } from 'react-router';

import { Button } from '@/components/ui/Button';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { EmptyState, ErrorNotice } from '@/components/ui/States';
import { queryKeys } from '@/hooks/queries';
import { useAuth } from '@/hooks/useAuth';
import { analyticsApi } from '@/services/api';
import type { Alert } from '@/types/api';
import { formatDateTime, titleCase } from '@/utils/format';

export function AlertsList({ alerts }: { alerts: Alert[] }) {
  const { can } = useAuth();
  const queryClient = useQueryClient();
  const [error, setError] = useState<unknown>(null);
  const acknowledge = useMutation({
    mutationFn: (id: number) => analyticsApi.acknowledgeAlert(id),
    onSuccess: () => {
      setError(null);
      void queryClient.invalidateQueries({ queryKey: queryKeys.alerts });
    },
    onError: setError,
  });

  if (alerts.length === 0) {
    return (
      <EmptyState
        title="No alerts recorded"
        hint="Alerts appear when rules detect high defect rates, faults, quarantines, or overdue orders."
      />
    );
  }

  return (
    <div className="flex flex-col gap-2">
      {error !== null && <ErrorNotice error={error} />}
      <ul className="divide-y divide-border">
        {alerts.map((alert) => (
          <li key={alert.id} className="flex flex-wrap items-start justify-between gap-2 py-2.5">
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <StatusBadge status={alert.severity} />
                <span className="text-xs text-ink-muted">{titleCase(alert.alert_type)}</span>
                <span className="text-xs text-ink-faint">{formatDateTime(alert.created_at)}</span>
              </div>
              <p className="mt-1 text-sm text-ink">
                {alert.message}
                {alert.production_order_id !== null && (
                  <>
                    {' '}
                    <Link
                      to="/orders"
                      className="text-xs text-accent hover:underline"
                      aria-label={`Open orders for alert ${alert.id}`}
                    >
                      View orders
                    </Link>
                  </>
                )}
              </p>
            </div>
            {alert.acknowledged_at ? (
              <span className="text-xs text-ink-faint">
                Acknowledged {formatDateTime(alert.acknowledged_at)}
              </span>
            ) : (
              can('alert.acknowledge') && (
                <Button
                  size="sm"
                  busy={acknowledge.isPending && acknowledge.variables === alert.id}
                  onClick={() => acknowledge.mutate(alert.id)}
                  aria-label={`Acknowledge alert ${alert.id}`}
                >
                  Acknowledge
                </Button>
              )
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
