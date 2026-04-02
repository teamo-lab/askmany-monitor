-- 违禁词监控看板 - PostgreSQL Schema
-- Based on FORBIDDEN_WORD_DASHBOARD_SPEC.md Section 6

-- 启用扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- 6.2 小时级统计快照
-- ============================================================
CREATE TABLE hourly_stats (
    id              BIGSERIAL PRIMARY KEY,
    timestamp_utc   TIMESTAMPTZ NOT NULL,
    weekday         SMALLINT NOT NULL,           -- 0=Mon, 6=Sun (ISO weekday)
    hour_utc        SMALLINT NOT NULL,           -- 0-23
    total_requests  INTEGER NOT NULL DEFAULT 0,
    blocked_count   INTEGER NOT NULL DEFAULT 0,
    block_rate      NUMERIC(6,4) NOT NULL DEFAULT 0,
    user_uv         INTEGER NOT NULL DEFAULT 0,
    conv_uv         INTEGER NOT NULL DEFAULT 0,
    categories      JSONB NOT NULL DEFAULT '{}',
    directions      JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_hourly_stats_timestamp UNIQUE (timestamp_utc)
);

CREATE INDEX idx_hourly_stats_timestamp_brin ON hourly_stats USING BRIN (timestamp_utc);
CREATE INDEX idx_hourly_stats_wow ON hourly_stats (weekday, hour_utc, timestamp_utc DESC);

COMMENT ON TABLE hourly_stats IS '违禁词小时级统计快照，每小时采集一次';
COMMENT ON COLUMN hourly_stats.categories IS '一级风险分类计数, JSONB格式: {"abuse":N,"porn":N,...}';
COMMENT ON COLUMN hourly_stats.directions IS '触发方向计数, JSONB格式: {"output":N,"input":N,...}';
COMMENT ON COLUMN hourly_stats.user_uv IS '受影响用户UV (仅shumei来源, upstream_api无username字段)';

-- ============================================================
-- 6.3 原始事件表
-- ============================================================
CREATE TABLE forbidden_events (
    id              BIGSERIAL PRIMARY KEY,
    event_time      TIMESTAMPTZ NOT NULL,
    username        VARCHAR(64),
    conv_id         VARCHAR(64) NOT NULL,
    direction       VARCHAR(20) NOT NULL,
    risk_level      VARCHAR(10) NOT NULL,
    risk_description VARCHAR(200),
    category        VARCHAR(20) NOT NULL,
    source          VARCHAR(20) NOT NULL,
    text_preview    VARCHAR(200),
    raw_data        JSONB,
    cls_log_id      VARCHAR(64),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_events_time_brin ON forbidden_events USING BRIN (event_time);
CREATE INDEX idx_events_category ON forbidden_events (category, event_time DESC);
CREATE INDEX idx_events_direction ON forbidden_events (direction, event_time DESC);
CREATE INDEX idx_events_username ON forbidden_events (username, event_time DESC) WHERE username IS NOT NULL;
CREATE INDEX idx_events_conv_id ON forbidden_events (conv_id);
CREATE UNIQUE INDEX idx_events_cls_log_id ON forbidden_events (cls_log_id) WHERE cls_log_id IS NOT NULL;

COMMENT ON TABLE forbidden_events IS '违禁词事件明细，从CLS同步';
COMMENT ON COLUMN forbidden_events.text_preview IS '触发文本前200字，用于页面预览';
COMMENT ON COLUMN forbidden_events.raw_data IS '数美完整审核结果JSON，可选存储';

-- ============================================================
-- 6.4 告警记录
-- ============================================================
CREATE TABLE alert_history (
    id              BIGSERIAL PRIMARY KEY,
    timestamp_utc   TIMESTAMPTZ NOT NULL,
    severity        VARCHAR(4) NOT NULL,
    rules_triggered JSONB NOT NULL,
    details         JSONB NOT NULL,
    notified_via    VARCHAR(50)[] NOT NULL DEFAULT '{}',
    acknowledged    BOOLEAN NOT NULL DEFAULT FALSE,
    acknowledged_by VARCHAR(100),
    acknowledged_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_alerts_time ON alert_history (timestamp_utc DESC);
CREATE INDEX idx_alerts_severity ON alert_history (severity, timestamp_utc DESC);
CREATE INDEX idx_alerts_unacked ON alert_history (acknowledged, timestamp_utc DESC) WHERE NOT acknowledged;

COMMENT ON TABLE alert_history IS '告警历史记录';

-- ============================================================
-- 6.5 系统配置表
-- ============================================================
CREATE TABLE system_config (
    key             VARCHAR(100) PRIMARY KEY,
    value           JSONB NOT NULL,
    description     VARCHAR(500),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by      VARCHAR(100)
);

INSERT INTO system_config (key, value, description) VALUES
('thresholds.min_blocked_count', '20', '最低样本量，低于此值跳过告警'),
('thresholds.block_rate_pct', '3.5', '拦截率告警阈值 (%)'),
('thresholds.wow_spike_ratio', '2.0', '周同比飙升倍数阈值'),
('thresholds.wow_min_base', '10', '周同比最低基数'),
('thresholds.affected_users_uv', '100', '受影响用户UV告警阈值 (人/小时)'),
('alert.cooldown_hours', '2', '同规则重复告警冷却时间 (小时)'),
('alert.consecutive_hours', '1', '连续超阈值N小时才告警'),
('alert.enable_feishu_call', 'false', '是否启用飞书电话通知 (二期)');

COMMENT ON TABLE system_config IS '系统配置KV存储，支持通过API动态修改';
