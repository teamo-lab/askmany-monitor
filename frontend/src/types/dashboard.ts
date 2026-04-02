export interface KPI {
  block_rate: number;
  blocked_count: number;
  user_uv: number;
  total_requests: number;
  block_rate_delta: number;
  blocked_count_delta: number;
  user_uv_delta: number;
  total_requests_delta: number;
}

export interface HourlyEntry {
  timestamp: string;
  total_requests: number;
  blocked_count: number;
  block_rate: number;
  user_uv: number;
  conv_uv: number;
  categories: Record<string, number>;
  directions: Record<string, number>;
  last_week_blocked: number | null;
  last_week_block_rate: number | null;
  wow_ratio: number | null;
}

export interface OverviewResponse {
  kpi: KPI;
  hourly: HourlyEntry[];
}
