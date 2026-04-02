import { Fragment, useEffect, useState } from 'react';
import useSWR from 'swr';
import { useTimeRange } from '../context/TimeRangeContext';
import { useDrilldown } from '../context/DrilldownContext';

interface EventRow {
  id: number;
  event_time: string;
  username: string | null;
  direction: string;
  risk_level: string;
  risk_description: string;
  category: string;
  source: string;
  conv_id: string;
  text_preview: string | null;
}

const fetcher = (url: string) => fetch(url).then((r) => r.json());

export function EventTable() {
  const [page, setPage] = useState(1);
  const [category, setCategory] = useState('');
  const [direction, setDirection] = useState('');
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const { range } = useTimeRange();
  const { filters } = useDrilldown();

  // Sync drilldown category filter
  useEffect(() => {
    if (filters.category) {
      setCategory(filters.category);
      setPage(1);
    }
  }, [filters.category]);

  const from = range.from.toISOString();
  const to = range.to.toISOString();

  let url = `/api/dashboard/events?from_dt=${from}&to_dt=${to}&page=${page}&size=20`;
  if (category) url += `&category=${category}`;
  if (direction) url += `&direction=${direction}`;

  const { data } = useSWR(url, fetcher, { refreshInterval: 60000 });
  const events: EventRow[] = data?.data ?? [];
  const total = data?.total ?? 0;
  const pages = data?.pages ?? 0;

  const categories = ['', 'abuse', 'porn', 'politics', 'ban', 'ad', 'violence', 'other'];
  const directions = ['', 'output', 'input', 'strict_text', 'upstream_api'];

  return (
    <div style={{ marginTop: '24px' }}>
      <h3>事件明细</h3>

      <div style={{ display: 'flex', gap: '12px', marginBottom: '12px' }}>
        <select value={category} onChange={(e) => { setCategory(e.target.value); setPage(1); }}>
          <option value="">全部分类</option>
          {categories.filter(Boolean).map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <select value={direction} onChange={(e) => { setDirection(e.target.value); setPage(1); }}>
          <option value="">全部方向</option>
          {directions.filter(Boolean).map((d) => <option key={d} value={d}>{d}</option>)}
        </select>
        <span style={{ color: '#868E96', fontSize: '0.85em', alignSelf: 'center' }}>
          共 {total} 条
        </span>
      </div>

      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85em' }}>
        <thead>
          <tr style={{ borderBottom: '2px solid #DEE2E6', textAlign: 'left' }}>
            <th style={{ padding: '8px' }}>时间</th>
            <th style={{ padding: '8px' }}>用户</th>
            <th style={{ padding: '8px' }}>方向</th>
            <th style={{ padding: '8px' }}>风险分类</th>
            <th style={{ padding: '8px' }}>等级</th>
            <th style={{ padding: '8px' }}>来源</th>
          </tr>
        </thead>
        <tbody>
          {events.map((evt) => (
            <Fragment key={evt.id}>
              <tr
                key={evt.id}
                onClick={() => setExpandedId(expandedId === evt.id ? null : evt.id)}
                style={{ borderBottom: '1px solid #F1F3F5', cursor: 'pointer' }}
              >
                <td style={{ padding: '8px' }}>
                  {new Date(evt.event_time).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' })}
                </td>
                <td style={{ padding: '8px' }}>{evt.username ?? '-'}</td>
                <td style={{ padding: '8px' }}>{evt.direction}</td>
                <td style={{ padding: '8px' }}>{evt.risk_description}</td>
                <td style={{ padding: '8px' }}>{evt.risk_level}</td>
                <td style={{ padding: '8px' }}>{evt.source}</td>
              </tr>
              {expandedId === evt.id && (
                <tr key={`${evt.id}-detail`}>
                  <td colSpan={6} style={{ padding: '12px', background: '#F8F9FA', fontSize: '0.9em' }}>
                    <strong>触发文本:</strong> {evt.text_preview ?? '(无)'}
                    <br />
                    <strong>会话ID:</strong> {evt.conv_id}
                  </td>
                </tr>
              )}
            </Fragment>
          ))}
        </tbody>
      </table>

      {pages > 1 && (
        <div style={{ display: 'flex', gap: '8px', marginTop: '12px', justifyContent: 'center' }}>
          <button disabled={page <= 1} onClick={() => setPage(page - 1)}>上一页</button>
          <span>{page} / {pages}</span>
          <button disabled={page >= pages} onClick={() => setPage(page + 1)}>下一页</button>
        </div>
      )}
    </div>
  );
}
