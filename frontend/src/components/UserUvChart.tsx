import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
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
}

export function UserUvChart({ data }: Props) {
  const chartData = data.map((d) => ({
    time: dayjs(d.timestamp).tz('Asia/Shanghai').format('MM-DD HH:mm'),
    uv: d.user_uv,
  }));

  return (
    <div>
      <div style={{ fontSize: '0.8em', color: '#868E96', marginBottom: 8 }}>
        仅含 shumei 来源
      </div>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="time" fontSize={12} />
          <YAxis fontSize={12} />
          <Tooltip />
          <Legend />
          <Line
            type="monotone"
            dataKey="uv"
            stroke="#4C6EF5"
            strokeWidth={2}
            dot={false}
            name="用户UV"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
