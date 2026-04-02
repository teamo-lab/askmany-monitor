import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';
import type { HourlyEntry } from '../types/dashboard';
import { DIRECTION_COLORS } from '../constants/colors';

dayjs.extend(utc);
dayjs.extend(timezone);

interface Props {
  data: HourlyEntry[];
}

const DIRECTIONS = ['output', 'input', 'strict_text', 'upstream_api'];

export function DirectionChart({ data }: Props) {
  const chartData = data.map((d) => ({
    time: dayjs(d.timestamp).tz('Asia/Shanghai').format('MM-DD HH:mm'),
    ...d.directions,
  }));

  return (
    <div>
      <ResponsiveContainer width="100%" height={300}>
        <AreaChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="time" fontSize={12} />
          <YAxis fontSize={12} />
          <Tooltip />
          <Legend />
          {DIRECTIONS.map((dir) => (
            <Area
              key={dir}
              type="monotone"
              dataKey={dir}
              stackId="1"
              stroke={DIRECTION_COLORS[dir]}
              fill={DIRECTION_COLORS[dir]}
              fillOpacity={0.6}
              name={dir}
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
