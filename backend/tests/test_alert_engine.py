"""TDD tests for alert engine."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models import AlertHistory, HourlyStat, SystemConfig
from app.services.alert_engine import evaluate_alerts, load_thresholds


@pytest.fixture
async def seed_stats(db_session):
    """Seed data for alert testing."""
    now = datetime(2026, 4, 2, 14, 0, 0, tzinfo=timezone.utc)

    # Current hour: high block rate, high wow ratio
    current = HourlyStat(
        timestamp_utc=now,
        weekday=now.weekday(),
        hour_utc=now.hour,
        total_requests=8000,
        blocked_count=320,  # 4% block rate > 3.5% threshold
        block_rate=0.04,
        user_uv=110,  # > 100 threshold
        conv_uv=150,
        categories={"abuse": 160, "porn": 80, "politics": 50, "ban": 30},
        directions={"output": 220, "input": 50, "upstream_api": 50},
    )
    db_session.add(current)

    # Last week same hour: lower counts for wow comparison
    last_week = HourlyStat(
        timestamp_utc=now - timedelta(days=7),
        weekday=now.weekday(),
        hour_utc=now.hour,
        total_requests=7000,
        blocked_count=100,  # wow_ratio = 320/100 = 3.2x > 2.0 threshold
        block_rate=0.0143,
        user_uv=50,
        conv_uv=80,
        categories={"abuse": 50, "porn": 30},
        directions={"output": 70, "input": 30},
    )
    db_session.add(last_week)

    await db_session.commit()
    return now


class TestAlertEngine:
    async def test_all_rules_trigger(self, seed_stats, db_session):
        now = seed_stats
        alerts = await evaluate_alerts(now, db_session)

        assert len(alerts) > 0
        rules = alerts[0]["rules_triggered"]
        assert "block_rate" in rules
        assert "wow_spike" in rules
        assert "affected_users" in rules

    async def test_alert_written_to_db(self, seed_stats, db_session):
        now = seed_stats
        await evaluate_alerts(now, db_session)

        result = await db_session.execute(select(AlertHistory))
        history = result.scalars().all()
        assert len(history) == 1
        assert history[0].severity == "P0"

    async def test_min_sample_skip(self, db_session):
        """Low blocked_count should skip all alert rules."""
        now = datetime(2026, 4, 2, 3, 0, 0, tzinfo=timezone.utc)
        stat = HourlyStat(
            timestamp_utc=now,
            weekday=now.weekday(),
            hour_utc=now.hour,
            total_requests=500,
            blocked_count=5,  # < 20 min threshold
            block_rate=0.01,
            user_uv=3,
            conv_uv=5,
            categories={},
            directions={},
        )
        db_session.add(stat)
        await db_session.commit()

        alerts = await evaluate_alerts(now, db_session)
        assert len(alerts) == 0

    async def test_no_stats_no_alert(self, db_session):
        now = datetime(2026, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
        alerts = await evaluate_alerts(now, db_session)
        assert len(alerts) == 0

    async def test_cooldown_prevents_repeat(self, seed_stats, db_session):
        """Second evaluation within cooldown should not create duplicate alert."""
        now = seed_stats
        await evaluate_alerts(now, db_session)
        # Run again for same hour
        await evaluate_alerts(now, db_session)

        result = await db_session.execute(select(AlertHistory))
        history = result.scalars().all()
        assert len(history) == 1  # Only 1, not 2

    async def test_block_rate_only(self, db_session):
        """Only block_rate rule triggers when others are within thresholds."""
        now = datetime(2026, 4, 2, 15, 0, 0, tzinfo=timezone.utc)
        stat = HourlyStat(
            timestamp_utc=now,
            weekday=now.weekday(),
            hour_utc=now.hour,
            total_requests=5000,
            blocked_count=200,  # 4% > 3.5%
            block_rate=0.04,
            user_uv=50,  # < 100
            conv_uv=80,
            categories={"abuse": 100},
            directions={"output": 150},
        )
        db_session.add(stat)
        await db_session.commit()

        alerts = await evaluate_alerts(now, db_session)
        assert len(alerts) == 1
        rules = alerts[0]["rules_triggered"]
        assert "block_rate" in rules
        assert "affected_users" not in rules

    async def test_custom_thresholds_trigger_alert(self, db_session):
        """User-configured lower threshold should trigger alert that defaults would miss."""
        now = datetime(2026, 4, 2, 16, 0, 0, tzinfo=timezone.utc)
        stat = HourlyStat(
            timestamp_utc=now,
            weekday=now.weekday(),
            hour_utc=now.hour,
            total_requests=10000,
            blocked_count=60,  # 0.6% block rate — below default 3.5%, above custom 0.5%
            block_rate=0.006,
            user_uv=30,
            conv_uv=40,
            categories={"abuse": 30},
            directions={"output": 40},
        )
        db_session.add(stat)
        await db_session.commit()

        # With defaults (3.5%), no alert
        alerts = await evaluate_alerts(now, db_session)
        assert len(alerts) == 0

        # Clean up the alert history for re-evaluation
        # With user-configured threshold (0.5%), alert triggers
        custom = {"block_rate_pct": 0.5}
        alerts = await evaluate_alerts(now, db_session, thresholds=custom)
        assert len(alerts) == 1
        assert "block_rate" in alerts[0]["rules_triggered"]


class TestLoadThresholds:
    async def test_load_thresholds_from_system_config(self, db_session):
        """_load_thresholds reads thresholds.* keys and strips prefix."""
        db_session.add(SystemConfig(key="thresholds.block_rate_pct", value=0.5))
        db_session.add(SystemConfig(key="thresholds.min_blocked_count", value=10))
        db_session.add(SystemConfig(key="other.setting", value="ignored"))
        await db_session.commit()

        thresholds = await load_thresholds(db_session)
        assert thresholds == {"block_rate_pct": 0.5, "min_blocked_count": 10.0}

    async def test_load_thresholds_string_values(self, db_session):
        """String-encoded JSON values are parsed to float."""
        db_session.add(SystemConfig(key="thresholds.block_rate_pct", value="0.5"))
        await db_session.commit()

        thresholds = await load_thresholds(db_session)
        assert thresholds["block_rate_pct"] == 0.5
        assert isinstance(thresholds["block_rate_pct"], float)

    async def test_load_thresholds_empty(self, db_session):
        """No thresholds configured returns empty dict."""
        thresholds = await load_thresholds(db_session)
        assert thresholds == {}
