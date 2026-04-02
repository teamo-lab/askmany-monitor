import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { BlockRateChart } from '../src/components/BlockRateChart';
import { EventCountChart } from '../src/components/EventCountChart';
import { DirectionChart } from '../src/components/DirectionChart';
import { UserUvChart } from '../src/components/UserUvChart';
import type { HourlyEntry } from '../src/types/dashboard';

const mockHourly: HourlyEntry[] = [
  {
    timestamp: '2026-04-01T14:00:00Z',
    total_requests: 8034,
    blocked_count: 307,
    block_rate: 0.0382,
    user_uv: 67,
    conv_uv: 120,
    categories: { abuse: 156, porn: 78, politics: 41, ban: 15, other: 8 },
    directions: { output: 213, input: 22, upstream_api: 52 },
    last_week_blocked: 114,
    last_week_block_rate: 0.0142,
    wow_ratio: 2.69,
  },
  {
    timestamp: '2026-04-01T15:00:00Z',
    total_requests: 9000,
    blocked_count: 250,
    block_rate: 0.0278,
    user_uv: 55,
    conv_uv: 100,
    categories: { abuse: 120, porn: 65, politics: 35, ban: 20, other: 10 },
    directions: { output: 180, input: 30, upstream_api: 40 },
    last_week_blocked: 200,
    last_week_block_rate: 0.0222,
    wow_ratio: 1.25,
  },
];

describe('BlockRateChart', () => {
  it('renders without crashing', () => {
    const { container } = render(<BlockRateChart data={mockHourly} />);
    expect(container.querySelector('.recharts-responsive-container')).toBeInTheDocument();
  });
});

describe('EventCountChart', () => {
  it('renders without crashing', () => {
    const { container } = render(<EventCountChart data={mockHourly} />);
    expect(container.querySelector('.recharts-responsive-container')).toBeInTheDocument();
  });
});

describe('DirectionChart', () => {
  it('renders without crashing', () => {
    const { container } = render(<DirectionChart data={mockHourly} />);
    expect(container.querySelector('.recharts-responsive-container')).toBeInTheDocument();
  });
});

describe('UserUvChart', () => {
  it('renders without crashing', () => {
    const { container } = render(<UserUvChart data={mockHourly} />);
    expect(container.querySelector('.recharts-responsive-container')).toBeInTheDocument();
  });

  it('shows shumei-only note', () => {
    render(<UserUvChart data={mockHourly} />);
    expect(screen.getByText(/仅含 shumei 来源/)).toBeInTheDocument();
  });
});
