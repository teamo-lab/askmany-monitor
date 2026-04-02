from datetime import datetime, timezone


def _utcnow():
    return datetime.now(timezone.utc)

from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    JSON,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# PostgreSQL uses ARRAY(String), SQLite falls back to JSON for testing
NotifiedViaType = JSON().with_variant(PG_ARRAY(String(50)), "postgresql")

TZDateTime = DateTime(timezone=True)


class Base(DeclarativeBase):
    pass


class HourlyStat(Base):
    __tablename__ = "hourly_stats"

    id: Mapped[int] = mapped_column(primary_key=True)
    timestamp_utc: Mapped[datetime] = mapped_column(TZDateTime, nullable=False)
    weekday: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    hour_utc: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    total_requests: Mapped[int] = mapped_column(Integer, default=0)
    blocked_count: Mapped[int] = mapped_column(Integer, default=0)
    block_rate: Mapped[float] = mapped_column(Numeric(6, 4), default=0)
    user_uv: Mapped[int] = mapped_column(Integer, default=0)
    conv_uv: Mapped[int] = mapped_column(Integer, default=0)
    categories: Mapped[dict] = mapped_column(JSON, default=dict)
    directions: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=_utcnow)

    __table_args__ = (
        UniqueConstraint("timestamp_utc", name="uq_hourly_stats_timestamp"),
    )


class ForbiddenEvent(Base):
    __tablename__ = "forbidden_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_time: Mapped[datetime] = mapped_column(TZDateTime, nullable=False)
    username: Mapped[str | None] = mapped_column(String(64))
    conv_id: Mapped[str] = mapped_column(String(64), nullable=False)
    direction: Mapped[str] = mapped_column(String(20), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(10), nullable=False)
    risk_description: Mapped[str | None] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    text_preview: Mapped[str | None] = mapped_column(String(200))
    raw_data: Mapped[dict | None] = mapped_column(JSON)
    cls_log_id: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=_utcnow)


class AlertHistory(Base):
    __tablename__ = "alert_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    timestamp_utc: Mapped[datetime] = mapped_column(TZDateTime, nullable=False)
    severity: Mapped[str] = mapped_column(String(4), nullable=False)
    rules_triggered: Mapped[dict] = mapped_column(JSON, nullable=False)
    details: Mapped[dict] = mapped_column(JSON, nullable=False)
    notified_via: Mapped[list] = mapped_column(NotifiedViaType, default=list)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    acknowledged_by: Mapped[str | None] = mapped_column(String(100))
    acknowledged_at: Mapped[datetime | None] = mapped_column(TZDateTime)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=_utcnow)


class SystemConfig(Base):
    __tablename__ = "system_config"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    updated_at: Mapped[datetime] = mapped_column(TZDateTime, default=_utcnow)
    updated_by: Mapped[str | None] = mapped_column(String(100))
