import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';
import type { HourlyEntry } from '../types/dashboard';

dayjs.extend(utc);
dayjs.extend(timezone);

interface Props {
  data: HourlyEntry[];
  threshold?: number;
}

export function BlockRateChart({ data, threshold = 0.035 }: Props) {
  const chartData = data.map((d) => ({
    time: dayjs(d.timestamp).tz('Asia/Shanghai').format('MM-DD HH:mm'),
    rate: +(d.block_rate * 100).toFixed(2),
    lastWeek: d.last_week_block_rate != null
      ? +(d.last_week_block_rate * 100).toFixed(2)
      : null,
  }));

  return (
    <div>
      <ResponsiveContainer width="100%" height={300}>
        <AreaChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="time" fontSize={12} />
          <YAxis unit="%" fontSize={12} />
          <Tooltip />
          <ReferenceLine
            y={threshold * 100}
            stroke="#E03131"
            strokeDasharray="5 5"
            label="阈值"
          />
          <Area
            type="monotone"
            dataKey="rate"
            stroke="#4C6EF5"
            fill="#4C6EF5"
            fillOpacity={0.15}
            name="拦截率"
          />
          <Area
            type="monotone"
            dataKey="lastWeek"
            stroke="#868E96"
            strokeDasharray="5 5"
            fill="none"
            name="上周同期"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
