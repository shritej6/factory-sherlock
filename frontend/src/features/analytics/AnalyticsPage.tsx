import { useState } from 'react';

import { CountBarChart } from '@/components/charts/CountBarChart';
import { DailyTrendChart } from '@/components/charts/DailyTrendChart';
import { DefectRateChart } from '@/components/charts/DefectRateChart';
import { PageHeader } from '@/components/ui/PageHeader';
import { ErrorState, LoadingState } from '@/components/ui/States';
import { useAnalyticsQuery, useOrderCounts, useQualitySummary } from '@/hooks/queries';
import { DEFAULT_WINDOW_END, DEFAULT_WINDOW_START, ORDER_STATUSES } from '@/types/constants';
import {
  pivotDailyTrend,
  toDefectCategorySeries,
  toDefectRateSeries,
  toOrderStatusSeries,
  toPassFailSeries,
} from '@/utils/chartTransforms';
import { FAIL_COLOR, PASS_COLOR, STATUS_SERIES_COLORS } from '@/utils/chartTheme';
import { toApiDateTime } from '@/utils/format';

import { SqlExplorer } from './SqlExplorer';
import type { TimeWindow } from './WindowControls';
import { WindowControls } from './WindowControls';

export function AnalyticsPage() {
  const [window, setWindow] = useState<TimeWindow>({
    start: DEFAULT_WINDOW_START,
    end: DEFAULT_WINDOW_END,
  });
  const params = {
    window_start: toApiDateTime(window.start),
    window_end: toApiDateTime(window.end),
  };
  const trend = useAnalyticsQuery('daily_production_trend', params);
  const defectRates = useAnalyticsQuery('machine_defect_rate_comparison', params);
  const recurring = useAnalyticsQuery('recurring_defects', params);
  const summary = useQualitySummary();
  const orderCounts = useOrderCounts(ORDER_STATUSES);
  const queries = [trend, defectRates, recurring, summary, orderCounts];
  const firstError = queries.find((q) => q.isError);

  return (
    <>
      <PageHeader
        title="Analytics and Reports"
        description="Charts are built from the same SQL queries the SQL Explorer runs."
      />
      <div className="panel mb-4 p-4 lg:max-w-xl">
        <WindowControls value={window} onChange={setWindow} />
      </div>
      {firstError && (
        <div className="mb-4">
          <ErrorState
            error={firstError.error}
            onRetry={() => queries.forEach((q) => void q.refetch())}
          />
        </div>
      )}
      {queries.some((q) => q.isPending) && <LoadingState label="Loading charts" />}
      <div className="mb-4 grid grid-cols-1 gap-4 xl:grid-cols-2">
        {trend.data && <DailyTrendChart trend={pivotDailyTrend(trend.data.rows)} />}
        {defectRates.data && <DefectRateChart points={toDefectRateSeries(defectRates.data.rows)} />}
        {summary.data && (
          <CountBarChart
            title="Pass and fail distribution"
            description="All inspections recorded in the database."
            points={toPassFailSeries(summary.data)}
            colors={{ Pass: PASS_COLOR, Fail: FAIL_COLOR }}
          />
        )}
        {recurring.data && (
          <CountBarChart
            title="Defect categories"
            description="Defect occurrences across all machines in the window."
            points={toDefectCategorySeries(recurring.data.rows)}
            layout="vertical"
          />
        )}
        {orderCounts.data && (
          <CountBarChart
            title="Production orders by status"
            description="Every order in the database, grouped by status."
            points={toOrderStatusSeries(orderCounts.data)}
            colors={STATUS_SERIES_COLORS}
          />
        )}
      </div>
      <SqlExplorer defaultWindow={window} />
    </>
  );
}
