import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import type { DailyTrend } from '@/utils/chartTransforms';
import {
  AXIS_COLOR,
  AXIS_LINE_COLOR,
  GRID_COLOR,
  seriesColor,
  TOOLTIP_STYLE,
} from '@/utils/chartTheme';

import { ChartFrame } from './ChartFrame';

export function DailyTrendChart({ trend }: { trend: DailyTrend }) {
  return (
    <ChartFrame
      title="Daily production trend"
      description="Units produced per day, one series per machine."
      empty={trend.points.length === 0}
      tableRows={trend.points}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={trend.points} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid stroke={GRID_COLOR} vertical={false} />
          <XAxis
            dataKey="date"
            tick={{ fill: AXIS_COLOR, fontSize: 12 }}
            axisLine={{ stroke: AXIS_LINE_COLOR }}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: AXIS_COLOR, fontSize: 12 }}
            axisLine={false}
            tickLine={false}
            width={44}
          />
          <Tooltip contentStyle={TOOLTIP_STYLE} cursor={{ fill: GRID_COLOR }} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          {trend.machines.map((machine, index) => (
            <Bar
              key={machine}
              dataKey={machine}
              fill={seriesColor(index)}
              radius={[2, 2, 0, 0]}
              maxBarSize={40}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </ChartFrame>
  );
}
