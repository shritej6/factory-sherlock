import {
  Bar,
  BarChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import type { DefectRatePoint } from '@/utils/chartTransforms';
import {
  AXIS_COLOR,
  AXIS_LINE_COLOR,
  FAIL_COLOR,
  GRID_COLOR,
  REFERENCE_COLOR,
  TOOLTIP_STYLE,
} from '@/utils/chartTheme';

import { ChartFrame } from './ChartFrame';

function percentTick(value: number): string {
  const percent = value * 100;
  return `${percent % 1 === 0 ? percent : percent.toFixed(1)}%`;
}

export function DefectRateChart({ points }: { points: DefectRatePoint[] }) {
  const fleet = points[0]?.fleetRate ?? 0;
  const tableRows = points.map((p) => ({
    machine: p.machine,
    inspected: p.inspected,
    failed: p.failed,
    defect_rate: p.defectRate,
    fleet_defect_rate: p.fleetRate,
  }));
  return (
    <ChartFrame
      title="Defect rate by machine"
      description={`Failed inspections divided by inspections in the window. Dashed line: fleet rate ${(fleet * 100).toFixed(1)}%.`}
      empty={points.length === 0}
      tableRows={tableRows}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={points} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid stroke={GRID_COLOR} vertical={false} />
          <XAxis
            dataKey="machine"
            tick={{ fill: AXIS_COLOR, fontSize: 12 }}
            axisLine={{ stroke: AXIS_LINE_COLOR }}
            tickLine={false}
          />
          <YAxis
            tickFormatter={percentTick}
            tick={{ fill: AXIS_COLOR, fontSize: 12 }}
            axisLine={false}
            tickLine={false}
            width={44}
          />
          <Tooltip
            contentStyle={TOOLTIP_STYLE}
            cursor={{ fill: GRID_COLOR }}
            formatter={(value, _name, item) => {
              const point = item.payload as DefectRatePoint;
              return [
                `${(Number(value) * 100).toFixed(1)}% (${point.failed} of ${point.inspected})`,
                'Defect rate',
              ];
            }}
          />
          <ReferenceLine y={fleet} stroke={REFERENCE_COLOR} strokeDasharray="4 4" />
          <Bar dataKey="defectRate" fill={FAIL_COLOR} radius={[2, 2, 0, 0]} maxBarSize={56} />
        </BarChart>
      </ResponsiveContainer>
    </ChartFrame>
  );
}
