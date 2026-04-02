import useSWR from 'swr';
import { fetchOverview } from '../api/dashboard';
import type { OverviewResponse } from '../types/dashboard';
import { MOCK_DATA } from './mockData';

export function useDashboard(hours = 24) {
  const { data, error, isLoading } = useSWR<OverviewResponse>(
    `overview-${hours}`,
    () => fetchOverview(hours),
    { refreshInterval: 60000, fallbackData: MOCK_DATA }
  );

  return { data: data ?? MOCK_DATA, error, isLoading };
}
