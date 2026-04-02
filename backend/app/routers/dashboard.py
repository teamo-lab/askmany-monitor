"""Dashboard API endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import AlertHistory, ForbiddenEvent, SystemConfig
from app.services.dashboard import get_hourly, get_overview

router = APIRouter(prefix="/api", tags=["dashboard"])


# --- Dashboard ---

@router.get("/dashboard/overview")
async def overview(
    hours: int = Query(default=24, ge=1, le=720),
    session: AsyncSession = Depends(get_session),
):
    return await get_overview(hours=hours, session=session)


@router.get("/dashboard/hourly")
async def hourly(
    from_dt: datetime = Query(...),
    to_dt: datetime = Query(...),
    session: AsyncSession = Depends(get_session),
):
    return {"data": await get_hourly(from_dt=from_dt, to_dt=to_dt, session=session)}


@router.get("/dashboard/events")
async def events(
    from_dt: datetime = Query(...),
    to_dt: datetime = Query(...),
    category: str | None = Query(default=None),
    direction: str | None = Query(default=None),
    source: str | None = Query(default=None),
    username: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    query = select(ForbiddenEvent).where(
        ForbiddenEvent.event_time >= from_dt,
        ForbiddenEvent.event_time < to_dt,
    )
    count_query = select(func.count()).select_from(ForbiddenEvent).where(
        ForbiddenEvent.event_time >= from_dt,
        ForbiddenEvent.event_time < to_dt,
    )

    if category:
        query = query.where(ForbiddenEvent.category == category)
        count_query = count_query.where(ForbiddenEvent.category == category)
    if direction:
        query = query.where(ForbiddenEvent.direction == direction)
        count_query = count_query.where(ForbiddenEvent.direction == direction)
    if source:
        query = query.where(ForbiddenEvent.source == source)
        count_query = count_query.where(ForbiddenEvent.source == source)
    if username:
        query = query.where(ForbiddenEvent.username.ilike(f"%{username}%"))
        count_query = count_query.where(ForbiddenEvent.username.ilike(f"%{username}%"))

    total_result = await session.execute(count_query)
    total = total_result.scalar()

    query = query.order_by(ForbiddenEvent.event_time.desc())
    query = query.offset((page - 1) * size).limit(size)

    result = await session.execute(query)
    rows = result.scalars().all()

    return {
        "data": [
            {
                "id": r.id,
                "event_time": r.event_time.isoformat(),
                "username": r.username,
                "direction": r.direction,
                "risk_level": r.risk_level,
                "risk_description": r.risk_description,
                "category": r.category,
                "source": r.source,
                "conv_id": r.conv_id,
                "text_preview": r.text_preview,
            }
            for r in rows
        ],
        "total": total,
        "page": page,
        "pages": (total + size - 1) // size if total else 0,
    }


@router.get("/dashboard/risk-types")
async def risk_types(
    from_dt: datetime = Query(...),
    to_dt: datetime = Query(...),
    limit: int = Query(default=10, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
):
    query = (
        select(
            ForbiddenEvent.risk_description,
            func.count().label("count"),
        )
        .where(
            ForbiddenEvent.event_time >= from_dt,
            ForbiddenEvent.event_time < to_dt,
        )
        .group_by(ForbiddenEvent.risk_description)
        .order_by(func.count().desc())
        .limit(limit)
    )
    result = await session.execute(query)
    rows = result.all()

    total_count = sum(r.count for r in rows) if rows else 0

    return {
        "data": [
            {
                "risk_description": r.risk_description,
                "count": r.count,
                "pct": round(r.count / total_count * 100, 1) if total_count else 0,
            }
            for r in rows
        ]
    }


# --- Alerts ---

@router.get("/alerts")
async def alerts_list(
    from_dt: datetime = Query(...),
    to_dt: datetime = Query(...),
    severity: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    query = select(AlertHistory).where(
        AlertHistory.timestamp_utc >= from_dt,
        AlertHistory.timestamp_utc < to_dt,
    )
    if severity:
        query = query.where(AlertHistory.severity == severity)
    query = query.order_by(AlertHistory.timestamp_utc.desc())

    result = await session.execute(query)
    rows = result.scalars().all()

    return {
        "data": [
            {
                "id": r.id,
                "timestamp_utc": r.timestamp_utc.isoformat(),
                "severity": r.severity,
                "rules_triggered": r.rules_triggered,
                "details": r.details,
                "notified_via": r.notified_via,
                "acknowledged": r.acknowledged,
                "acknowledged_by": r.acknowledged_by,
            }
            for r in rows
        ]
    }


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: int,
    body: dict,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(AlertHistory).where(AlertHistory.id == alert_id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.acknowledged = True
    alert.acknowledged_by = body.get("acknowledged_by", "unknown")
    alert.acknowledged_at = datetime.now(timezone.utc)
    await session.commit()

    return {"id": alert.id, "acknowledged": True, "acknowledged_by": alert.acknowledged_by}


# --- Config ---

@router.get("/config")
async def get_config(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(SystemConfig))
    rows = result.scalars().all()
    return {r.key: r.value for r in rows}


@router.patch("/config")
async def patch_config(
    updates: dict,
    session: AsyncSession = Depends(get_session),
):
    for key, value in updates.items():
        result = await session.execute(
            select(SystemConfig).where(SystemConfig.key == key)
        )
        row = result.scalar_one_or_none()
        if row:
            row.value = value
        else:
            session.add(SystemConfig(key=key, value=value))

    await session.commit()
    return await get_config(session=session)
