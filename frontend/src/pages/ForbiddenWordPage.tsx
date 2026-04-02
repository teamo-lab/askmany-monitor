import { Card, Col, Row } from 'antd';
import { AlertBanner } from '../components/AlertBanner';
import { KpiCards } from '../components/KpiCards';
import { BlockRateChart } from '../components/BlockRateChart';
import { EventCountChart } from '../components/EventCountChart';
import { DirectionChart } from '../components/DirectionChart';
import { UserUvChart } from '../components/UserUvChart';
import { RiskTypeTable } from '../components/RiskTypeTable';
import { EventTable } from '../components/EventTable';
import { useDashboard } from '../hooks/useDashboard';
import { useTimeRange } from '../context/TimeRangeContext';

export function ForbiddenWordPage() {
  const { range } = useTimeRange();
  const { data, error } = useDashboard(range.hours);

  return (
    <div>
      <AlertBanner />

      {error && (
        <div style={{ padding: '12px', background: '#FFF3BF', borderRadius: '4px', marginBottom: '16px' }}>
          API 连接失败，当前展示 mock 数据
        </div>
      )}

      <KpiCards kpi={data.kpi} />

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={24}>
          <Card title="拦截率趋势" size="small" bordered={false}>
            <BlockRateChart data={data.hourly} />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={12}>
          <Card title="事件分类" size="small" bordered={false}>
            <EventCountChart data={data.hourly} />
          </Card>
        </Col>
        <Col span={12}>
          <Card title="方向分布" size="small" bordered={false}>
            <DirectionChart data={data.hourly} />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={12}>
          <Card title="用户UV趋势" size="small" bordered={false}>
            <UserUvChart data={data.hourly} />
          </Card>
        </Col>
        <Col span={12}>
          <Card title="风险类型 Top 10" size="small" bordered={false}>
            <RiskTypeTable />
          </Card>
        </Col>
      </Row>

      <Row style={{ marginTop: 16 }}>
        <Col span={24}>
          <Card title="事件明细" size="small" bordered={false}>
            <EventTable />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
