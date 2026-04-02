"""TDD Red phase: tests for dashboard API endpoints."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models import HourlyStat


@pytest.fixture
async def seeded_db(db_session):
    """Seed 24 hours of data + 7 days ago for week-over-week."""
    now = datetime(2026, 4, 2, 10, 0, 0, tzinfo=timezone.utc)

    for i in range(24):
        ts = now - timedelta(hours=24 - i)
        stat = HourlyStat(
            timestamp_utc=ts,
            weekday=ts.weekday(),
            hour_utc=ts.hour,
            total_requests=8000 + i * 100,
            blocked_count=100 + i * 5,
            block_rate=round((100 + i * 5) / (8000 + i * 100), 4),
            user_uv=50 + i,
            conv_uv=80 + i * 2,
            categories={"abuse": 50 + i, "porn": 30 + i, "politics": 20},
            directions={"output": 70 + i, "input": 15, "upstream_api": 15 + i},
        )
        db_session.add(stat)

    # Last week same period (for WoW comparison)
    for i in range(24):
        ts = now - timedelta(days=7, hours=24 - i)
        stat = HourlyStat(
            timestamp_utc=ts,
            weekday=ts.weekday(),
            hour_utc=ts.hour,
            total_requests=7000 + i * 80,
            blocked_count=80 + i * 3,
            block_rate=round((80 + i * 3) / (7000 + i * 80), 4),
            user_uv=40 + i,
            conv_uv=60 + i,
            categories={"abuse": 40, "porn": 25, "politics": 15},
            directions={"output": 55, "input": 10, "upstream_api": 15},
        )
        db_session.add(stat)

    await db_session.commit()
    return now


class TestOverviewAPI:
    async def test_overview_returns_kpi(self, seeded_db, db_session):
        from app.services.dashboard import get_overview

        now = seeded_db
        result = await get_overview(hours=24, session=db_session, now=now)

        assert "kpi" in result
        kpi = result["kpi"]
        assert "block_rate" in kpi
        assert "blocked_count" in kpi
        assert "user_uv" in kpi
        assert "total_requests" in kpi

    async def test_overview_kpi_values(self, seeded_db, db_session):
        from app.services.dashboard import get_overview

        now = seeded_db
        result = await get_overview(hours=24, session=db_session, now=now)

        kpi = result["kpi"]
        # Latest hour stats (the 24th entry, i=23)
        assert kpi["total_requests"] == 8000 + 23 * 100  # 10300
        assert kpi["blocked_count"] == 100 + 23 * 5      # 215
        assert kpi["user_uv"] == 50 + 23                  # 73

    async def test_overview_returns_hourly_data(self, seeded_db, db_session):
        from app.services.dashboard import get_overview

        now = seeded_db
        result = await get_overview(hours=24, session=db_session, now=now)

        assert "hourly" in result
        assert len(result["hourly"]) == 24

    async def test_overview_hourly_has_wow(self, seeded_db, db_session):
        from app.services.dashboard import get_overview

        now = seeded_db
        result = await get_overview(hours=24, session=db_session, now=now)

        hourly = result["hourly"]
        # Each hourly entry should have last_week data
        for entry in hourly:
            assert "last_week_blocked" in entry

    async def test_overview_empty_db(self, db_session):
        from app.services.dashboard import get_overview

        now = datetime(2026, 4, 2, 10, 0, 0, tzinfo=timezone.utc)
        result = await get_overview(hours=24, session=db_session, now=now)

        assert result["kpi"]["blocked_count"] == 0
        assert result["kpi"]["total_requests"] == 0
        assert len(result["hourly"]) == 0


class TestHourlyAPI:
    async def test_hourly_returns_data(self, seeded_db, db_session):
        from app.services.dashboard import get_hourly

        now = seeded_db
        from_dt = now - timedelta(hours=24)
        result = await get_hourly(from_dt=from_dt, to_dt=now, session=db_session)

        assert len(result) == 24

    async def test_hourly_entry_fields(self, seeded_db, db_session):
        from app.services.dashboard import get_hourly

        now = seeded_db
        from_dt = now - timedelta(hours=24)
        result = await get_hourly(from_dt=from_dt, to_dt=now, session=db_session)

        entry = result[0]
        assert "timestamp" in entry
        assert "total_requests" in entry
        assert "blocked_count" in entry
        assert "block_rate" in entry
        assert "user_uv" in entry
        assert "categories" in entry
        assert "directions" in entry
        assert "last_week_blocked" in entry
        assert "wow_ratio" in entry

    async def test_hourly_wow_ratio(self, seeded_db, db_session):
        from app.services.dashboard import get_hourly

        now = seeded_db
        from_dt = now - timedelta(hours=24)
        result = await get_hourly(from_dt=from_dt, to_dt=now, session=db_session)

        # Every entry should have a non-None wow_ratio since we seeded last week data
        for entry in result:
            assert entry["last_week_blocked"] is not None
            assert entry["wow_ratio"] is not None

    async def test_hourly_empty_range(self, db_session):
        from app.services.dashboard import get_hourly

        from_dt = datetime(2026, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
        to_dt = datetime(2026, 5, 2, 0, 0, 0, tzinfo=timezone.utc)
        result = await get_hourly(from_dt=from_dt, to_dt=to_dt, session=db_session)

        assert len(result) == 0


class TestAPIEndpoints:
    async def test_overview_endpoint(self, client):
        resp = await client.get("/api/dashboard/overview?hours=24")
        assert resp.status_code == 200
        data = resp.json()
        assert "kpi" in data
        assert "hourly" in data

    async def test_hourly_endpoint(self, client):
        resp = await client.get(
            "/api/dashboard/hourly?from_dt=2026-04-01T00:00:00Z&to_dt=2026-04-02T00:00:00Z"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
