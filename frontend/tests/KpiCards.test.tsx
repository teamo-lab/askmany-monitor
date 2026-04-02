import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { KpiCards } from '../src/components/KpiCards';
import type { KPI } from '../src/types/dashboard';

const mockKpi: KPI = {
  block_rate: 0.0382,
  blocked_count: 307,
  user_uv: 67,
  total_requests: 8034,
  block_rate_delta: 0.005,
  blocked_count_delta: 15,
  user_uv_delta: -3,
  total_requests_delta: 200,
};

describe('KpiCards', () => {
  it('renders 4 KPI cards', () => {
    render(<KpiCards kpi={mockKpi} />);
    expect(screen.getByText('拦截率')).toBeInTheDocument();
    expect(screen.getByText('拦截事件数')).toBeInTheDocument();
    expect(screen.getByText('受影响用户')).toBeInTheDocument();
    expect(screen.getByText('总请求量')).toBeInTheDocument();
  });

  it('displays block rate as percentage', () => {
    render(<KpiCards kpi={mockKpi} />);
    expect(screen.getByText('3.82%')).toBeInTheDocument();
  });

  it('displays blocked count', () => {
    render(<KpiCards kpi={mockKpi} />);
    expect(screen.getByText('307')).toBeInTheDocument();
  });

  it('displays user UV', () => {
    render(<KpiCards kpi={mockKpi} />);
    expect(screen.getByText('67')).toBeInTheDocument();
  });

  it('displays total requests with comma formatting', () => {
    render(<KpiCards kpi={mockKpi} />);
    expect(screen.getByText('8,034')).toBeInTheDocument();
  });

  it('shows alert state when block rate exceeds threshold', () => {
    const alertKpi = { ...mockKpi, block_rate: 0.04 };
    const { container } = render(<KpiCards kpi={alertKpi} threshold={0.035} />);
    const alertCard = container.querySelector('.kpi-alert');
    expect(alertCard).toBeInTheDocument();
  });
});
