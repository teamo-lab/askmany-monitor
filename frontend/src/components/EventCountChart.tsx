import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Legend,
} from 'recharts';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';
import type { HourlyEntry } from '../types/dashboard';
import { CATEGORY_COLORS } from '../constants/colors';

dayjs.extend(utc);
dayjs.extend(timezone);

interface Props {
  data: HourlyEntry[];
}

const CATEGORIES = ['abuse', 'porn', 'politics', 'ban', 'ad', 'violence', 'other'];
const CATEGORY_LABELS: Record<string, string> = {
  abuse: '辱骂',
  porn: '色情',
  politics: '涉政',
  ban: '违禁',
  ad: '广告',
  violence: '暴力',
  other: '其他',
};

export function EventCountChart({ data }: Props) {
  const chartData = data.map((d) => ({
    time: dayjs(d.timestamp).tz('Asia/Shanghai').format('MM-DD HH:mm'),
    ...d.categories,
  }));

  return (
    <div>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="time" fontSize={12} />
          <YAxis fontSize={12} />
          <Tooltip />
          <Legend />
          {CATEGORIES.map((cat) => (
            <Bar
              key={cat}
              dataKey={cat}
              stackId="a"
              fill={CATEGORY_COLORS[cat]}
              name={CATEGORY_LABELS[cat] || cat}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
