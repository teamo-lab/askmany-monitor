"""TDD Red phase: tests for ORM models."""

from datetime import datetime, timezone

from sqlalchemy import select

from app.models import (
    AlertHistory,
    Base,
    ForbiddenEvent,
    HourlyStat,
    SystemConfig,
)


async def test_hourly_stat_create_and_query(db_session):
    ts = datetime(2026, 4, 1, 14, 0, 0, tzinfo=timezone.utc)
    stat = HourlyStat(
        timestamp_utc=ts,
        weekday=1,  # Tuesday
        hour_utc=14,
        total_requests=8034,
        blocked_count=307,
        block_rate=0.0382,
        user_uv=67,
        conv_uv=120,
        categories={"abuse": 156, "porn": 78, "politics": 41},
        directions={"output": 213, "upstream_api": 52, "input": 22},
    )
    db_session.add(stat)
    await db_session.commit()

    result = await db_session.execute(
        select(HourlyStat).where(HourlyStat.timestamp_utc == ts)
    )
    row = result.scalar_one()
    assert row.total_requests == 8034
    assert row.blocked_count == 307
    assert row.categories["abuse"] == 156
    assert row.directions["output"] == 213
    assert row.user_uv == 67


async def test_hourly_stat_unique_timestamp(db_session):
    ts = datetime(2026, 4, 1, 14, 0, 0, tzinfo=timezone.utc)
    stat1 = HourlyStat(
        timestamp_utc=ts, weekday=1, hour_utc=14,
        total_requests=100, blocked_count=5, block_rate=0.05,
    )
    stat2 = HourlyStat(
        timestamp_utc=ts, weekday=1, hour_utc=14,
        total_requests=200, blocked_count=10, block_rate=0.05,
    )
    db_session.add(stat1)
    await db_session.commit()

    db_session.add(stat2)
    try:
        await db_session.commit()
        assert False, "Should have raised IntegrityError"
    except Exception:
        await db_session.rollback()


async def test_forbidden_event_create(db_session):
    event = ForbiddenEvent(
        event_time=datetime(2026, 4, 1, 14, 5, 30, tzinfo=timezone.utc),
        username="#13221638719",
        conv_id="2b17f8c9-ef52-405f-b831-test",
        direction="output",
        risk_level="REJECT",
        risk_description="色情:色情描写:重度色情描写",
        category="porn",
        source="shumei",
        text_preview="test content preview",
    )
    db_session.add(event)
    await db_session.commit()

    result = await db_session.execute(
        select(ForbiddenEvent).where(ForbiddenEvent.category == "porn")
    )
    row = result.scalar_one()
    assert row.username == "#13221638719"
    assert row.direction == "output"
    assert row.risk_level == "REJECT"


async def test_forbidden_event_nullable_username(db_session):
    event = ForbiddenEvent(
        event_time=datetime(2026, 4, 1, 14, 5, 30, tzinfo=timezone.utc),
        username=None,
        conv_id="conv-test",
        direction="output",
        risk_level="REJECT",
        category="abuse",
        source="upstream_api",
    )
    db_session.add(event)
    await db_session.commit()

    result = await db_session.execute(
        select(ForbiddenEvent).where(ForbiddenEvent.source == "upstream_api")
    )
    row = result.scalar_one()
    assert row.username is None


async def test_alert_history_create(db_session):
    alert = AlertHistory(
        timestamp_utc=datetime(2026, 4, 1, 14, 0, 0, tzinfo=timezone.utc),
        severity="P0",
        rules_triggered=["block_rate", "wow_spike"],
        details={"block_rate": 0.038, "threshold": 0.035},
        notified_via=["page"],
    )
    db_session.add(alert)
    await db_session.commit()

    result = await db_session.execute(
        select(AlertHistory).where(AlertHistory.severity == "P0")
    )
    row = result.scalar_one()
    assert row.acknowledged is False
    assert "block_rate" in row.rules_triggered


async def test_system_config_create(db_session):
    config = SystemConfig(
        key="thresholds.block_rate_pct",
        value=3.5,
        description="拦截率告警阈值 (%)",
    )
    db_session.add(config)
    await db_session.commit()

    result = await db_session.execute(
        select(SystemConfig).where(SystemConfig.key == "thresholds.block_rate_pct")
    )
    row = result.scalar_one()
    assert row.value == 3.5


async def test_health_endpoint(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_all_tables_exist(db_engine):
    """Verify all 4 tables are created."""
    async with db_engine.connect() as conn:
        tables = await conn.run_sync(
            lambda sync_conn: Base.metadata.tables.keys()
        )
    expected = {"hourly_stats", "forbidden_events", "alert_history", "system_config"}
    assert expected == set(tables)
