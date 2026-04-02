"""Tests for iteration 2 APIs: events, risk-types, alerts, config."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models import AlertHistory, ForbiddenEvent, HourlyStat, SystemConfig


@pytest.fixture
async def seed_events(db_session):
    """Seed forbidden_events for testing."""
    base_time = datetime(2026, 4, 1, 14, 0, 0, tzinfo=timezone.utc)
    events = [
        ForbiddenEvent(
            event_time=base_time + timedelta(minutes=i),
            username=f"#user{i}" if i % 3 != 0 else None,
            conv_id=f"conv-{i}",
            direction="output" if i % 2 == 0 else "input",
            risk_level="REJECT",
            risk_description="辱骂:侮辱:轻度" if i % 3 == 0 else "色情:色情描写:重度色情描写",
            category="abuse" if i % 3 == 0 else "porn",
            source="shumei" if i % 3 != 0 else "upstream_api",
            text_preview=f"test content {i}",
        )
        for i in range(25)
    ]
    db_session.add_all(events)
    await db_session.commit()
    return base_time


@pytest.fixture
async def seed_alerts(db_session):
    """Seed alert_history for testing."""
    now = datetime(2026, 4, 2, 14, 0, 0, tzinfo=timezone.utc)
    alert = AlertHistory(
        timestamp_utc=now,
        severity="P0",
        rules_triggered=["block_rate", "wow_spike"],
        details={"block_rate_actual": 4.2, "block_rate_threshold": 3.5},
        notified_via=["page"],
    )
    db_session.add(alert)
    await db_session.commit()
    return now


@pytest.fixture
async def seed_config(db_session):
    configs = [
        SystemConfig(key="thresholds.block_rate_pct", value=3.5, description="拦截率阈值"),
        SystemConfig(key="thresholds.min_blocked_count", value=20, description="最低样本量"),
    ]
    db_session.add_all(configs)
    await db_session.commit()


class TestEventsAPI:
    async def test_events_endpoint(self, client, seed_events):
        resp = await client.get(
            "/api/dashboard/events?from_dt=2026-04-01T00:00:00Z&to_dt=2026-04-02T00:00:00Z"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert "total" in data
        assert data["total"] == 25
        assert len(data["data"]) == 20  # default page size

    async def test_events_pagination(self, client, seed_events):
        resp = await client.get(
            "/api/dashboard/events?from_dt=2026-04-01T00:00:00Z&to_dt=2026-04-02T00:00:00Z&page=2&size=20"
        )
        data = resp.json()
        assert len(data["data"]) == 5  # 25 - 20

    async def test_events_filter_category(self, client, seed_events):
        resp = await client.get(
            "/api/dashboard/events?from_dt=2026-04-01T00:00:00Z&to_dt=2026-04-02T00:00:00Z&category=abuse"
        )
        data = resp.json()
        for evt in data["data"]:
            assert evt["category"] == "abuse"

    async def test_events_filter_direction(self, client, seed_events):
        resp = await client.get(
            "/api/dashboard/events?from_dt=2026-04-01T00:00:00Z&to_dt=2026-04-02T00:00:00Z&direction=output"
        )
        data = resp.json()
        for evt in data["data"]:
            assert evt["direction"] == "output"


class TestRiskTypesAPI:
    async def test_risk_types_endpoint(self, client, seed_events):
        resp = await client.get(
            "/api/dashboard/risk-types?from_dt=2026-04-01T00:00:00Z&to_dt=2026-04-02T00:00:00Z"
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) > 0
        assert "risk_description" in data[0]
        assert "count" in data[0]
        assert "pct" in data[0]


class TestAlertsAPI:
    async def test_alerts_list(self, client, seed_alerts):
        resp = await client.get(
            "/api/alerts?from_dt=2026-04-01T00:00:00Z&to_dt=2026-04-03T00:00:00Z"
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["severity"] == "P0"

    async def test_alerts_filter_severity(self, client, seed_alerts):
        resp = await client.get(
            "/api/alerts?from_dt=2026-04-01T00:00:00Z&to_dt=2026-04-03T00:00:00Z&severity=P1"
        )
        data = resp.json()["data"]
        assert len(data) == 0

    async def test_acknowledge_alert(self, client, seed_alerts, db_session):
        # Get alert ID
        resp = await client.get(
            "/api/alerts?from_dt=2026-04-01T00:00:00Z&to_dt=2026-04-03T00:00:00Z"
        )
        alert_id = resp.json()["data"][0]["id"]

        # Acknowledge it
        resp = await client.post(
            f"/api/alerts/{alert_id}/acknowledge",
            json={"acknowledged_by": "operator_test"},
        )
        assert resp.status_code == 200
        assert resp.json()["acknowledged"] is True


class TestEvaluateAPI:
    async def test_evaluate_no_data(self, client):
        resp = await client.post("/api/alerts/evaluate", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert data["alerts"] == []
        assert "target_hour" in data

    async def test_evaluate_with_target_hour(self, client, db_session):
        """Evaluate with explicit target_hour and data that triggers alert."""
        target = datetime(2026, 4, 2, 10, 0, 0, tzinfo=timezone.utc)
        stat = HourlyStat(
            timestamp_utc=target,
            weekday=target.weekday(),
            hour_utc=target.hour,
            total_requests=10000,
            blocked_count=500,
            block_rate=0.05,  # 5% > 3.5% default
            user_uv=200,
            conv_uv=300,
            categories={"abuse": 300},
            directions={"output": 400},
        )
        db_session.add(stat)
        await db_session.commit()

        resp = await client.post(
            "/api/alerts/evaluate",
            json={"target_hour": "2026-04-02T10:00:00+00:00"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["target_hour"] == "2026-04-02T10:00:00+00:00"
        assert len(data["alerts"]) == 1
        assert "block_rate" in data["alerts"][0]["rules_triggered"]

    async def test_evaluate_uses_custom_thresholds(self, client, db_session):
        """Evaluate picks up user-configured thresholds from system_config."""
        target = datetime(2026, 4, 2, 11, 0, 0, tzinfo=timezone.utc)
        stat = HourlyStat(
            timestamp_utc=target,
            weekday=target.weekday(),
            hour_utc=target.hour,
            total_requests=10000,
            blocked_count=60,
            block_rate=0.006,  # 0.6% — below default 3.5%, above custom 0.5%
            user_uv=30,
            conv_uv=40,
            categories={"abuse": 30},
            directions={"output": 40},
        )
        db_session.add(stat)
        db_session.add(SystemConfig(key="thresholds.block_rate_pct", value=0.5))
        await db_session.commit()

        resp = await client.post(
            "/api/alerts/evaluate",
            json={"target_hour": "2026-04-02T11:00:00+00:00"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["alerts"]) == 1
        assert data["thresholds_applied"]["block_rate_pct"] == 0.5

    async def test_evaluate_invalid_target_hour(self, client):
        resp = await client.post(
            "/api/alerts/evaluate",
            json={"target_hour": "not-a-date"},
        )
        assert resp.status_code == 400


class TestConfigAPI:
    async def test_get_config(self, client, seed_config):
        resp = await client.get("/api/config")
        assert resp.status_code == 200
        data = resp.json()
        assert "thresholds.block_rate_pct" in data

    async def test_patch_config(self, client, seed_config):
        resp = await client.patch(
            "/api/config",
            json={"thresholds.block_rate_pct": 4.0},
        )
        assert resp.status_code == 200

        # Verify update
        resp = await client.get("/api/config")
        assert resp.json()["thresholds.block_rate_pct"] == 4.0
