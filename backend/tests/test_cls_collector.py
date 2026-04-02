"""TDD Red phase: tests for CLS data collection service."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select

from app.models import ForbiddenEvent, HourlyStat
from app.services.cls_collector import CLSCollector, get_category


class TestGetCategory:
    def test_abuse(self):
        assert get_category("辱骂:侮辱:轻度侮辱") == "abuse"

    def test_porn(self):
        assert get_category("色情:色情描写:重度色情描写") == "porn"

    def test_politics(self):
        assert get_category("涉政:涉政内容:敏感人物") == "politics"

    def test_ban(self):
        assert get_category("违禁:违禁品:毒品") == "ban"

    def test_ad(self):
        assert get_category("广告:推广:商业推广") == "ad"

    def test_violence(self):
        assert get_category("暴力:暴力行为:严重暴力") == "violence"

    def test_other(self):
        assert get_category("未知分类") == "other"

    def test_none(self):
        assert get_category(None) == "other"

    def test_empty(self):
        assert get_category("") == "other"


class TestCLSCollector:
    def test_parse_hourly_stats_response(self):
        records = [
            '{"hour_slot": "2026-04-01 14:00", "blocked_count": "307", "user_uv": "67", "conv_uv": "120"}',
        ]
        result = CLSCollector.parse_hourly_stats(records)
        assert len(result) == 1
        assert result[0]["blocked_count"] == 307
        assert result[0]["user_uv"] == 67
        assert result[0]["hour_slot"] == "2026-04-01 14:00"

    def test_parse_total_requests_response(self):
        records = [
            '{"hour_slot": "2026-04-01 14:00", "total_requests": "8034"}',
        ]
        result = CLSCollector.parse_total_requests(records)
        assert result["2026-04-01 14:00"] == 8034

    def test_parse_category_distribution(self):
        records = [
            '{"hour_slot": "2026-04-01 14:00", "category": "abuse", "cnt": "156"}',
            '{"hour_slot": "2026-04-01 14:00", "category": "porn", "cnt": "78"}',
        ]
        result = CLSCollector.parse_category_distribution(records)
        assert result["2026-04-01 14:00"] == {"abuse": 156, "porn": 78}

    def test_parse_direction_distribution(self):
        records = [
            '{"hour_slot": "2026-04-01 14:00", "direction": "output", "cnt": "213"}',
            '{"hour_slot": "2026-04-01 14:00", "direction": "input", "cnt": "22"}',
        ]
        result = CLSCollector.parse_direction_distribution(records)
        assert result["2026-04-01 14:00"] == {"output": 213, "input": 22}

    def test_parse_events_response(self):
        records = [
            '{"event_time": "2026-04-01 14:05:30.535107", "event_id": "output", "risk_level": "REJECT", "risk_description": "色情:色情描写:重度色情描写", "source": "shumei", "username": "#13221638719", "conv_id": "conv-123", "text": "some text content", "cls_log_id": "log-001"}',
        ]
        result = CLSCollector.parse_events(records)
        assert len(result) == 1
        evt = result[0]
        assert evt["direction"] == "output"
        assert evt["category"] == "porn"
        assert evt["username"] == "#13221638719"
        assert evt["text_preview"] == "some text content"
        assert evt["cls_log_id"] == "log-001"

    def test_parse_events_truncates_text(self):
        long_text = "x" * 300
        records = [
            f'{{"event_time": "2026-04-01 14:05:30", "event_id": "output", "risk_level": "REJECT", "risk_description": "辱骂:侮辱:轻度", "source": "shumei", "username": "#123", "conv_id": "c1", "text": "{long_text}"}}',
        ]
        result = CLSCollector.parse_events(records)
        assert len(result[0]["text_preview"]) == 200

    def test_parse_events_no_username(self):
        records = [
            '{"event_time": "2026-04-01 14:05:30", "event_id": "output", "risk_level": "REJECT", "risk_description": "辱骂:侮辱:轻度", "source": "upstream_api", "conv_id": "c1", "text": "test"}',
        ]
        result = CLSCollector.parse_events(records)
        assert result[0]["username"] is None


class TestCollectHourly:
    @pytest.fixture
    def collector(self):
        return CLSCollector(
            secret_id="test_id",
            secret_key="test_key",
            region="ap-hongkong",
            topic_id="test-topic-id",
        )

    async def test_collect_writes_hourly_stat(self, db_session, collector):
        target = datetime(2026, 4, 1, 14, 0, 0, tzinfo=timezone.utc)

        with patch.object(collector, "_query_cls") as mock_query:
            mock_query.side_effect = [
                # hourly stats
                ['{"hour_slot": "2026-04-01 14:00", "blocked_count": "307", "user_uv": "67", "conv_uv": "120"}'],
                # total requests
                ['{"hour_slot": "2026-04-01 14:00", "total_requests": "8034"}'],
                # categories
                ['{"hour_slot": "2026-04-01 14:00", "category": "abuse", "cnt": "156"}',
                 '{"hour_slot": "2026-04-01 14:00", "category": "porn", "cnt": "78"}'],
                # directions
                ['{"hour_slot": "2026-04-01 14:00", "direction": "output", "cnt": "213"}'],
                # events
                ['{"event_time": "2026-04-01 14:05:30", "event_id": "output", "risk_level": "REJECT", "risk_description": "色情:色情描写:重度色情描写", "source": "shumei", "username": "#123", "conv_id": "c1", "text": "test"}'],
            ]

            await collector.collect_hourly(target, db_session)

        result = await db_session.execute(
            select(HourlyStat).where(HourlyStat.timestamp_utc == target)
        )
        stat = result.scalar_one()
        assert stat.total_requests == 8034
        assert stat.blocked_count == 307
        assert stat.user_uv == 67
        assert float(stat.block_rate) == pytest.approx(307 / 8034, abs=0.001)
        assert stat.categories == {"abuse": 156, "porn": 78}
        assert stat.directions == {"output": 213}

    async def test_collect_writes_events(self, db_session, collector):
        target = datetime(2026, 4, 1, 14, 0, 0, tzinfo=timezone.utc)

        with patch.object(collector, "_query_cls") as mock_query:
            mock_query.side_effect = [
                ['{"hour_slot": "2026-04-01 14:00", "blocked_count": "10", "user_uv": "5", "conv_uv": "8"}'],
                ['{"hour_slot": "2026-04-01 14:00", "total_requests": "500"}'],
                [],
                [],
                ['{"event_time": "2026-04-01 14:05:30", "event_id": "output", "risk_level": "REJECT", "risk_description": "色情:色情描写:重度", "source": "shumei", "username": "#123", "conv_id": "c1", "text": "test"}'],
            ]

            await collector.collect_hourly(target, db_session)

        result = await db_session.execute(select(ForbiddenEvent))
        events = result.scalars().all()
        assert len(events) == 1
        assert events[0].category == "porn"
        assert events[0].direction == "output"

    async def test_collect_idempotent(self, db_session, collector):
        """Running collect twice for the same hour should upsert, not duplicate."""
        target = datetime(2026, 4, 1, 14, 0, 0, tzinfo=timezone.utc)
        mock_responses = [
            ['{"hour_slot": "2026-04-01 14:00", "blocked_count": "10", "user_uv": "5", "conv_uv": "8"}'],
            ['{"hour_slot": "2026-04-01 14:00", "total_requests": "500"}'],
            [], [], [],
        ]

        with patch.object(collector, "_query_cls") as mock_query:
            mock_query.side_effect = mock_responses.copy()
            await collector.collect_hourly(target, db_session)

        with patch.object(collector, "_query_cls") as mock_query:
            mock_query.side_effect = [
                ['{"hour_slot": "2026-04-01 14:00", "blocked_count": "20", "user_uv": "10", "conv_uv": "15"}'],
                ['{"hour_slot": "2026-04-01 14:00", "total_requests": "600"}'],
                [], [], [],
            ]
            await collector.collect_hourly(target, db_session)

        result = await db_session.execute(select(HourlyStat))
        stats = result.scalars().all()
        assert len(stats) == 1
        assert stats[0].blocked_count == 20  # updated, not duplicated

    async def test_collect_events_dedup_by_cls_log_id(self, db_session, collector):
        """Events with same cls_log_id should not be duplicated on re-collect."""
        target = datetime(2026, 4, 1, 14, 0, 0, tzinfo=timezone.utc)
        event_record = '{"event_time": "2026-04-01 14:05:30", "event_id": "output", "risk_level": "REJECT", "risk_description": "辱骂:侮辱:轻度", "source": "shumei", "username": "#123", "conv_id": "c1", "text": "test", "cls_log_id": "log-dedup-001"}'

        base_responses = [
            ['{"hour_slot": "2026-04-01 14:00", "blocked_count": "10", "user_uv": "5", "conv_uv": "8"}'],
            ['{"hour_slot": "2026-04-01 14:00", "total_requests": "500"}'],
            [], [],
            [event_record],
        ]

        with patch.object(collector, "_query_cls") as mock_query:
            mock_query.side_effect = base_responses.copy()
            await collector.collect_hourly(target, db_session)

        # Second collection with same event
        with patch.object(collector, "_query_cls") as mock_query:
            mock_query.side_effect = [
                ['{"hour_slot": "2026-04-01 14:00", "blocked_count": "10", "user_uv": "5", "conv_uv": "8"}'],
                ['{"hour_slot": "2026-04-01 14:00", "total_requests": "500"}'],
                [], [],
                [event_record],
            ]
            await collector.collect_hourly(target, db_session)

        result = await db_session.execute(select(ForbiddenEvent))
        events = result.scalars().all()
        assert len(events) == 1  # deduped, not 2
        assert events[0].cls_log_id == "log-dedup-001"
