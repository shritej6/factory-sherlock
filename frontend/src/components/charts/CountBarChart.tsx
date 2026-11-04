import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import type { CountPoint } from '@/utils/chartTransforms';
import {
  AXIS_COLOR,
  AXIS_LINE_COLOR,
  GRID_COLOR,
  seriesColor,
  TOOLTIP_STYLE,
} from '@/utils/chartTheme';

import { ChartFrame } from './ChartFrame';

interface CountBarChartProps {
  title: string;
  description?: string;
  points: CountPoint[];
  colors?: Record<string, string>;
  layout?: 'horizontal' | 'vertical';
}

/** Category counts as bars; used for pass/fail, defect categories, and order status. */
export function CountBarChart({
  title,
  description,
  points,
  colors,
  layout = 'horizontal',
}: CountBarChartProps) {
  const vertical = layout === 'vertical';
  const total = points.reduce((sum, p) => sum + p.value, 0);
  const tableRows = points.map((p) => ({
    category: p.name,
    count: p.value,
    share: total ? p.value / total : 0,
  }));
  return (
    <ChartFrame
      title={title}
      description={description}
      empty={points.length === 0 || total === 0}
      height={vertical ? Math.max(180, points.length * 40 + 40) : 240}
      tableRows={tableRows}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={points}
          layout={vertical ? 'vertical' : 'horizontal'}
          margin={{ top: 8, right: 16, left: vertical ? 8 : 0, bottom: 0 }}
        >
          <CartesianGrid stroke={GRID_COLOR} horizontal={!vertical} vertical={vertical} />
          {vertical ? (
            <>
              <XAxis
                type="number"
                tick={{ fill: AXIS_COLOR, fontSize: 12 }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                type="category"
                dataKey="name"
                width={160}
                tick={{ fill: AXIS_COLOR, fontSize: 11 }}
                axisLine={false}
                tickLine={false}
              />
            </>
          ) : (
            <>
              <XAxis
                dataKey="name"
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
            </>
          )}
          <Tooltip
            contentStyle={TOOLTIP_STYLE}
            cursor={{ fill: GRID_COLOR }}
            formatter={(value) => [
              `${Number(value)} (${total ? ((Number(value) / total) * 100).toFixed(1) : '0.0'}%)`,
              'Count',
            ]}
          />
          <Bar dataKey="value" radius={vertical ? [0, 2, 2, 0] : [2, 2, 0, 0]} maxBarSize={48}>
            {points.map((point, index) => (
              <Cell key={point.name} fill={colors?.[point.name] ?? seriesColor(index)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartFrame>
  );
}
