import type { KPI } from '../types/dashboard';

interface Props {
  kpi: KPI;
  threshold?: number;
}

function formatNumber(n: number): string {
  return n.toLocaleString('en-US');
}

function DeltaIndicator({ value, suffix = '' }: { value: number; suffix?: string }) {
  if (value === 0) return <span style={{ color: '#868E96' }}>-</span>;
  const color = value > 0 ? '#E03131' : '#2F9E44';
  const arrow = value > 0 ? '\u2191' : '\u2193';
  return (
    <span style={{ color, fontSize: '0.85em' }}>
      {arrow} {Math.abs(value).toFixed(suffix === '%' ? 2 : 0)}{suffix}
    </span>
  );
}

export function KpiCards({ kpi, threshold = 0.035 }: Props) {
  const isAlert = kpi.block_rate > threshold;

  const cards = [
    {
      label: '拦截率',
      value: `${(kpi.block_rate * 100).toFixed(2)}%`,
      delta: <DeltaIndicator value={kpi.block_rate_delta * 100} suffix="%" />,
      alert: isAlert,
    },
    {
      label: '拦截事件数',
      value: String(kpi.blocked_count),
      delta: <DeltaIndicator value={kpi.blocked_count_delta} />,
      alert: false,
    },
    {
      label: '受影响用户',
      value: String(kpi.user_uv),
      delta: <DeltaIndicator value={kpi.user_uv_delta} />,
      alert: false,
    },
    {
      label: '总请求量',
      value: formatNumber(kpi.total_requests),
      delta: <DeltaIndicator value={kpi.total_requests_delta} />,
      alert: false,
    },
  ];

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
      {cards.map((card) => (
        <div
          key={card.label}
          className={card.alert ? 'kpi-alert' : undefined}
          style={{
            padding: '20px',
            borderRadius: '8px',
            background: card.alert ? '#FFF5F5' : '#F8F9FA',
            border: card.alert ? '2px solid #E03131' : '1px solid #DEE2E6',
          }}
        >
          <div style={{ fontSize: '0.85em', color: '#868E96', marginBottom: '8px' }}>
            {card.label}
          </div>
          <div style={{ fontSize: '1.8em', fontWeight: 700, marginBottom: '4px' }}>
            {card.value}
          </div>
          <div>{card.delta}</div>
        </div>
      ))}
    </div>
  );
}
