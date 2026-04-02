import { Button, DatePicker, Space } from 'antd';
import type { Dayjs } from 'dayjs';
import { useTimeRange } from '../context/TimeRangeContext';

const { RangePicker } = DatePicker;

const PRESETS = [
  { label: '1h', hours: 1 },
  { label: '6h', hours: 6 },
  { label: '12h', hours: 12 },
  { label: '24h', hours: 24 },
  { label: '7d', hours: 168 },
  { label: '30d', hours: 720 },
];

export function TimeRangeSelector() {
  const { range, setPreset, setCustom } = useTimeRange();

  const onRangeChange = (dates: [Dayjs | null, Dayjs | null] | null) => {
    if (dates && dates[0] && dates[1]) {
      setCustom(dates[0], dates[1]);
    }
  };

  return (
    <Space size="small">
      {PRESETS.map((p) => (
        <Button
          key={p.label}
          type={range.label === p.label ? 'primary' : 'default'}
          size="small"
          onClick={() => setPreset(p.hours, p.label)}
        >
          {p.label}
        </Button>
      ))}
      <RangePicker
        size="small"
        showTime
        onChange={onRangeChange as any}
      />
    </Space>
  );
}
