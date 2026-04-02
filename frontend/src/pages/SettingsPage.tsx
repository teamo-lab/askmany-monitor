import { useEffect, useState } from 'react';
import { Button, Card, Form, InputNumber, message, Spin, Typography } from 'antd';

const { Title, Text } = Typography;

interface ConfigItem {
  key: string;
  label: string;
  description: string;
  suffix?: string;
  min?: number;
  max?: number;
  step?: number;
}

const CONFIG_ITEMS: ConfigItem[] = [
  { key: 'thresholds.min_blocked_count', label: '最低样本量', description: '低于此值跳过告警', suffix: '条', min: 0, step: 1 },
  { key: 'thresholds.block_rate_pct', label: '拦截率阈值', description: '超过此值触发告警', suffix: '%', min: 0, max: 100, step: 0.1 },
  { key: 'thresholds.wow_spike_ratio', label: '同比飙升倍数', description: '周同比超过此倍数触发告警', suffix: 'x', min: 1, step: 0.1 },
  { key: 'thresholds.wow_min_base', label: '同比最低基数', description: '上周同时段至少达到此数量才做同比', suffix: '条', min: 0, step: 1 },
  { key: 'thresholds.affected_users_uv', label: '受影响用户UV阈值', description: '每小时受影响用户超过此值触发告警', suffix: '人/小时', min: 0, step: 1 },
  { key: 'alert.cooldown_hours', label: '告警冷却时间', description: '同规则重复告警冷却时间', suffix: '小时', min: 0, step: 1 },
  { key: 'alert.consecutive_hours', label: '连续超阈值小时数', description: '连续超阈值N小时才告警', suffix: '小时', min: 1, step: 1 },
];

export function SettingsPage() {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetch('/api/config')
      .then((r) => r.json())
      .then((data) => {
        form.setFieldsValue(data);
        setLoading(false);
      })
      .catch(() => {
        message.error('加载配置失败');
        setLoading(false);
      });
  }, [form]);

  const onSave = async () => {
    setSaving(true);
    try {
      const values = form.getFieldsValue();
      const res = await fetch('/api/config', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values),
      });
      if (!res.ok) throw new Error();
      message.success('配置保存成功');
    } catch {
      message.error('保存失败');
    }
    setSaving(false);
  };

  if (loading) return <Spin style={{ display: 'block', margin: '100px auto' }} />;

  return (
    <Card>
      <Title level={4} style={{ marginBottom: 24 }}>告警配置</Title>
      <Form form={form} layout="vertical" style={{ maxWidth: 600 }}>
        {CONFIG_ITEMS.map((item) => (
          <Form.Item
            key={item.key}
            name={item.key}
            label={<Text strong>{item.label}</Text>}
            extra={<Text type="secondary">{item.description}</Text>}
          >
            <InputNumber
              style={{ width: '100%' }}
              min={item.min}
              max={item.max}
              step={item.step}
              addonAfter={item.suffix}
            />
          </Form.Item>
        ))}
        <Form.Item>
          <Button type="primary" onClick={onSave} loading={saving}>
            保存配置
          </Button>
        </Form.Item>
      </Form>
    </Card>
  );
}
