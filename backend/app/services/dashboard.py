"""Dashboard query service."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import HourlyStat


def _build_hourly_with_wow(stats: list, wow_map: dict) -> list[dict]:
    """Build hourly data list with week-over-week comparison from pre-fetched map."""
    hourly = []
    for stat in stats:
        wow_ts = stat.timestamp_utc - timedelta(days=7)
        wow_stat = wow_map.get(wow_ts)

        last_week_blocked = wow_stat.blocked_count if wow_stat else None
        last_week_block_rate = float(wow_stat.block_rate) if wow_stat else None
        wow_ratio = None
        if wow_stat and wow_stat.blocked_count > 0:
            wow_ratio = round(stat.blocked_count / wow_stat.blocked_count, 2)

        hourly.append({
            "timestamp": stat.timestamp_utc.isoformat(),
            "total_requests": stat.total_requests,
            "blocked_count": stat.blocked_count,
            "block_rate": float(stat.block_rate),
            "user_uv": stat.user_uv,
            "conv_uv": stat.conv_uv,
            "categories": stat.categories,
            "directions": stat.directions,
            "last_week_blocked": last_week_blocked,
            "last_week_block_rate": last_week_block_rate,
            "wow_ratio": wow_ratio,
        })
    return hourly


async def _fetch_wow_map(
    from_dt: datetime, to_dt: datetime, session: AsyncSession
) -> dict:
    """Batch-fetch last week's data in one query, return {timestamp: HourlyStat}."""
    wow_from = from_dt - timedelta(days=7)
    wow_to = to_dt - timedelta(days=7)
    wow_result = await session.execute(
        select(HourlyStat).where(
            HourlyStat.timestamp_utc >= wow_from,
            HourlyStat.timestamp_utc < wow_to,
        )
    )
    return {s.timestamp_utc: s for s in wow_result.scalars().all()}


async def get_overview(
    hours: int, session: AsyncSession, now: datetime | None = None
) -> dict:
    if now is None:
        now = datetime.now(timezone.utc)

    from_dt = now - timedelta(hours=hours)

    result = await session.execute(
        select(HourlyStat)
        .where(HourlyStat.timestamp_utc >= from_dt, HourlyStat.timestamp_utc < now)
        .order_by(HourlyStat.timestamp_utc)
    )
    stats = result.scalars().all()

    if not stats:
        return {
            "kpi": {
                "block_rate": 0,
                "blocked_count": 0,
                "user_uv": 0,
                "total_requests": 0,
                "block_rate_delta": 0,
                "blocked_count_delta": 0,
                "user_uv_delta": 0,
                "total_requests_delta": 0,
            },
            "hourly": [],
        }

    latest = stats[-1]
    prev = stats[-2] if len(stats) > 1 else None

    wow_map = await _fetch_wow_map(from_dt, now, session)
    hourly = _build_hourly_with_wow(stats, wow_map)

    kpi = {
        "block_rate": float(latest.block_rate),
        "blocked_count": latest.blocked_count,
        "user_uv": latest.user_uv,
        "total_requests": latest.total_requests,
        "block_rate_delta": float(latest.block_rate) - float(prev.block_rate) if prev else 0,
        "blocked_count_delta": latest.blocked_count - prev.blocked_count if prev else 0,
        "user_uv_delta": latest.user_uv - prev.user_uv if prev else 0,
        "total_requests_delta": latest.total_requests - prev.total_requests if prev else 0,
    }

    return {"kpi": kpi, "hourly": hourly}


async def get_hourly(
    from_dt: datetime, to_dt: datetime, session: AsyncSession
) -> list[dict]:
    result = await session.execute(
        select(HourlyStat)
        .where(HourlyStat.timestamp_utc >= from_dt, HourlyStat.timestamp_utc < to_dt)
        .order_by(HourlyStat.timestamp_utc)
    )
    stats = result.scalars().all()

    wow_map = await _fetch_wow_map(from_dt, to_dt, session)
    return _build_hourly_with_wow(stats, wow_map)
