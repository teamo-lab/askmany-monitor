import { useEffect, useRef } from 'react';
import useSWR from 'swr';
import { useTimeRange } from '../context/TimeRangeContext';

interface Alert {
  id: number;
  timestamp_utc: string;
  severity: string;
  rules_triggered: string[];
  details: Record<string, unknown>;
  acknowledged: boolean;
}

const fetcher = (url: string) => fetch(url).then((r) => r.json());

export function AlertBanner() {
  const { range } = useTimeRange();
  const from = range.from.toISOString();
  const to = range.to.toISOString();

  const { data, mutate } = useSWR(
    `/api/alerts?from_dt=${from}&to_dt=${to}`,
    fetcher,
    { refreshInterval: 60000 }
  );

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const alerts: Alert[] = data?.data ?? [];
  const unacked = alerts.filter((a) => !a.acknowledged);

  useEffect(() => {
    if (unacked.some((a) => a.severity === 'P0') && audioRef.current) {
      audioRef.current.play().catch(() => {});
    }
  }, [unacked.length]);

  const acknowledge = async (id: number) => {
    await fetch(`/api/alerts/${id}/acknowledge`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ acknowledged_by: 'dashboard_user' }),
    });
    mutate();
  };

  if (unacked.length === 0) return null;

  return (
    <>
      <audio ref={audioRef} src="data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=" />
      {unacked.map((alert) => {
        const bg = alert.severity === 'P0' ? '#FFF5F5' : alert.severity === 'INFO' ? '#FFF9DB' : '#F8F9FA';
        const border = alert.severity === 'P0' ? '#E03131' : alert.severity === 'INFO' ? '#F59F00' : '#DEE2E6';
        const rules = alert.rules_triggered.join(', ');
        const details = alert.details as Record<string, number>;

        return (
          <div
            key={alert.id}
            className="alert-banner"
            style={{
              padding: '12px 16px',
              marginBottom: '8px',
              borderRadius: '8px',
              background: bg,
              border: `2px solid ${border}`,
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <div>
              <strong>[{alert.severity}]</strong>{' '}
              违禁词告警 | {new Date(alert.timestamp_utc).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' })}
              <br />
              <span style={{ fontSize: '0.85em', color: '#495057' }}>
                触发规则: {rules}
                {details.block_rate_actual != null && ` | 拦截率 ${details.block_rate_actual}%`}
                {details.wow_ratio != null && ` | 同比 ${details.wow_ratio}x`}
              </span>
            </div>
            <button
              onClick={() => acknowledge(alert.id)}
              style={{
                padding: '4px 12px',
                borderRadius: '4px',
                border: '1px solid #DEE2E6',
                background: '#fff',
                cursor: 'pointer',
              }}
            >
              确认
            </button>
          </div>
        );
      })}
    </>
  );
}
