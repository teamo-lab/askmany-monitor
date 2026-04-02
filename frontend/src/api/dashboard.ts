import type { OverviewResponse } from '../types/dashboard';

const API_BASE = '/api';

export async function fetchOverview(hours = 24): Promise<OverviewResponse> {
  const res = await fetch(`${API_BASE}/dashboard/overview?hours=${hours}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}
