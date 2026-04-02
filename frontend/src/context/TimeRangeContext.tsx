import { createContext, useContext, useState, type ReactNode } from 'react';
import dayjs, { type Dayjs } from 'dayjs';

interface TimeRange {
  from: Dayjs;
  to: Dayjs;
  hours: number;
  label: string;
}

interface TimeRangeContextType {
  range: TimeRange;
  setPreset: (hours: number, label: string) => void;
  setCustom: (from: Dayjs, to: Dayjs) => void;
}

const defaultRange: TimeRange = {
  from: dayjs().subtract(24, 'hour'),
  to: dayjs(),
  hours: 24,
  label: '24h',
};

const TimeRangeContext = createContext<TimeRangeContextType>({
  range: defaultRange,
  setPreset: () => {},
  setCustom: () => {},
});

export function TimeRangeProvider({ children }: { children: ReactNode }) {
  const [range, setRange] = useState<TimeRange>(defaultRange);

  const setPreset = (hours: number, label: string) => {
    setRange({
      from: dayjs().subtract(hours, 'hour'),
      to: dayjs(),
      hours,
      label,
    });
  };

  const setCustom = (from: Dayjs, to: Dayjs) => {
    const hours = to.diff(from, 'hour');
    setRange({ from, to, hours, label: 'custom' });
  };

  return (
    <TimeRangeContext.Provider value={{ range, setPreset, setCustom }}>
      {children}
    </TimeRangeContext.Provider>
  );
}

export function useTimeRange() {
  return useContext(TimeRangeContext);
}
