import type { OverviewResponse } from '../types/dashboard';

function generateMockHourly() {
  const hourly = [];
  const now = new Date();
  for (let i = 23; i >= 0; i--) {
    const ts = new Date(now.getTime() - i * 3600000);
    ts.setMinutes(0, 0, 0);
    const blocked = Math.floor(100 + Math.random() * 200);
    const total = Math.floor(7000 + Math.random() * 5000);
    hourly.push({
      timestamp: ts.toISOString(),
      total_requests: total,
      blocked_count: blocked,
      block_rate: +(blocked / total).toFixed(4),
      user_uv: Math.floor(40 + Math.random() * 60),
      conv_uv: Math.floor(60 + Math.random() * 80),
      categories: {
        abuse: Math.floor(blocked * 0.48),
        porn: Math.floor(blocked * 0.30),
        politics: Math.floor(blocked * 0.15),
        ban: Math.floor(blocked * 0.05),
        other: Math.floor(blocked * 0.02),
      },
      directions: {
        output: Math.floor(blocked * 0.70),
        input: Math.floor(blocked * 0.10),
        strict_text: Math.floor(blocked * 0.05),
        upstream_api: Math.floor(blocked * 0.15),
      },
      last_week_blocked: Math.floor(80 + Math.random() * 150),
      last_week_block_rate: +(0.008 + Math.random() * 0.03).toFixed(4),
      wow_ratio: +(0.8 + Math.random() * 1.5).toFixed(2),
    });
  }
  return hourly;
}

const hourly = generateMockHourly();
const latest = hourly[hourly.length - 1];
const prev = hourly[hourly.length - 2];

export const MOCK_DATA: OverviewResponse = {
  kpi: {
    block_rate: latest.block_rate,
    blocked_count: latest.blocked_count,
    user_uv: latest.user_uv,
    total_requests: latest.total_requests,
    block_rate_delta: latest.block_rate - prev.block_rate,
    blocked_count_delta: latest.blocked_count - prev.blocked_count,
    user_uv_delta: latest.user_uv - prev.user_uv,
    total_requests_delta: latest.total_requests - prev.total_requests,
  },
  hourly,
};
