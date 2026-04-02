"""Alert rule engine per SPEC section 4."""

import json
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AlertHistory, HourlyStat, SystemConfig

logger = logging.getLogger(__name__)

# Default thresholds (can be overridden via system_config)
DEFAULT_THRESHOLDS = {
    "min_blocked_count": 20,
    "block_rate_pct": 3.5,
    "wow_spike_ratio": 2.0,
    "wow_min_base": 10,
    "affected_users_uv": 100,
    "cooldown_hours": 2,
}


THRESHOLD_PREFIX = "thresholds."


async def load_thresholds(session: AsyncSession) -> dict:
    """Load user-configured thresholds from system_config table."""
    result = await session.execute(
        select(SystemConfig).where(SystemConfig.key.like(f"{THRESHOLD_PREFIX}%"))
    )
    rows = result.scalars().all()
    thresholds = {}
    for row in rows:
        key = row.key[len(THRESHOLD_PREFIX):]
        value = row.value
        if isinstance(value, str):
            value = json.loads(value)
        thresholds[key] = float(value)
    return thresholds


async def evaluate_alerts(
    target_hour: datetime,
    session: AsyncSession,
    thresholds: dict | None = None,
) -> list[dict]:
    """Evaluate alert rules for the given hour. Returns list of triggered alerts."""
    cfg = {**DEFAULT_THRESHOLDS, **(thresholds or {})}

    # Fetch current hour stats
    result = await session.execute(
        select(HourlyStat).where(HourlyStat.timestamp_utc == target_hour)
    )
    stat = result.scalar_one_or_none()
    if not stat:
        return []

    # Rule 0: minimum sample check
    if stat.blocked_count < cfg["min_blocked_count"]:
        logger.info("Skipping alerts for %s: blocked_count=%d < min=%d",
                     target_hour, stat.blocked_count, cfg["min_blocked_count"])
        return []

    # Fetch last week same hour for WoW
    wow_ts = target_hour - timedelta(days=7)
    wow_result = await session.execute(
        select(HourlyStat).where(HourlyStat.timestamp_utc == wow_ts)
    )
    wow_stat = wow_result.scalar_one_or_none()

    # Evaluate rules
    triggered_rules = []
    details = {
        "timestamp": target_hour.isoformat(),
        "total_requests": stat.total_requests,
        "blocked_count": stat.blocked_count,
        "block_rate": float(stat.block_rate),
        "user_uv": stat.user_uv,
    }

    # Rule 1: block rate
    block_rate_pct = float(stat.block_rate) * 100
    if block_rate_pct > cfg["block_rate_pct"]:
        triggered_rules.append("block_rate")
        details["block_rate_threshold"] = cfg["block_rate_pct"]
        details["block_rate_actual"] = round(block_rate_pct, 2)

    # Rule 2: WoW spike
    if wow_stat and wow_stat.blocked_count >= cfg["wow_min_base"]:
        wow_ratio = stat.blocked_count / wow_stat.blocked_count
        details["wow_ratio"] = round(wow_ratio, 2)
        details["last_week_blocked"] = wow_stat.blocked_count
        if wow_ratio > cfg["wow_spike_ratio"]:
            triggered_rules.append("wow_spike")

    # Rule 3: affected users
    if stat.user_uv > cfg["affected_users_uv"]:
        triggered_rules.append("affected_users")
        details["user_uv_threshold"] = cfg["affected_users_uv"]

    if not triggered_rules:
        return []

    # Cooldown check: skip if alert exists within cooldown window
    cooldown_since = target_hour - timedelta(hours=cfg["cooldown_hours"])
    existing_alert = await session.execute(
        select(AlertHistory).where(
            AlertHistory.timestamp_utc > cooldown_since,
            AlertHistory.timestamp_utc <= target_hour,
        )
    )
    if existing_alert.scalar_one_or_none():
        logger.info("Alert exists within cooldown window %s~%s, skipping",
                     cooldown_since, target_hour)
        return []

    # Write alert
    alert = AlertHistory(
        timestamp_utc=target_hour,
        severity="P0",
        rules_triggered=triggered_rules,
        details=details,
        notified_via=["page"],
    )
    session.add(alert)
    await session.commit()

    alert_info = {
        "severity": "P0",
        "rules_triggered": triggered_rules,
        "details": details,
    }

    logger.warning("ALERT P0 for %s: rules=%s", target_hour, triggered_rules)
    return [alert_info]
