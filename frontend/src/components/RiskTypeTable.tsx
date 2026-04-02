import { Table } from 'antd';
import useSWR from 'swr';
import { useTimeRange } from '../context/TimeRangeContext';
import { useDrilldown } from '../context/DrilldownContext';

const fetcher = (url: string) => fetch(url).then((r) => r.json());

interface RiskType {
  risk_description: string;
  count: number;
  pct: number;
}

export function RiskTypeTable() {
  const { range } = useTimeRange();
  const { setFilters } = useDrilldown();

  const from = range.from.toISOString();
  const to = range.to.toISOString();

  const { data } = useSWR(
    `/api/dashboard/risk-types?from_dt=${from}&to_dt=${to}&limit=10`,
    fetcher,
    { refreshInterval: 60000 }
  );

  const rows: RiskType[] = data?.data ?? [];

  const columns = [
    { title: '#', key: 'rank', render: (_: unknown, __: unknown, i: number) => i + 1, width: 40 },
    { title: '风险描述', dataIndex: 'risk_description', key: 'risk_description' },
    { title: '数量', dataIndex: 'count', key: 'count', width: 80 },
    { title: '占比', key: 'pct', width: 80, render: (_: unknown, r: RiskType) => `${r.pct}%` },
  ];

  return (
    <Table
      dataSource={rows}
      columns={columns}
      rowKey="risk_description"
      size="small"
      pagination={false}
      onRow={(record) => ({
        onClick: () => {
          const desc = record.risk_description || '';
          const cat = desc.split(':')[0];
          const categoryMap: Record<string, string> = {
            '辱骂': 'abuse', '色情': 'porn', '涉政': 'politics',
            '违禁': 'ban', '广告': 'ad', '暴力': 'violence',
          };
          setFilters({ category: categoryMap[cat] || 'other' });
        },
        style: { cursor: 'pointer' },
      })}
    />
  );
}
