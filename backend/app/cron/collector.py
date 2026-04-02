"""Hourly CLS collection cron job."""

import logging
from datetime import datetime, timedelta, timezone

from app.config import settings
from app.database import AsyncSessionLocal
from app.services.alert_engine import evaluate_alerts, load_thresholds
from app.services.cls_collector import CLSCollector

logger = logging.getLogger(__name__)


async def run_hourly_collection():
    """Collect data for the previous complete hour, then evaluate alerts."""
    now = datetime.now(timezone.utc)
    target_hour = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)

    logger.info("Starting hourly collection for %s", target_hour.isoformat())

    try:
        collector = CLSCollector(
            secret_id=settings.tencent_secret_id,
            secret_key=settings.tencent_secret_key,
            region=settings.cls_region,
            topic_id=settings.cls_topic_id,
        )

        async with AsyncSessionLocal() as session:
            await collector.collect_hourly(target_hour, session)
            thresholds = await load_thresholds(session)
            await evaluate_alerts(target_hour, session, thresholds=thresholds)

        logger.info("Hourly collection completed for %s", target_hour.isoformat())
    except Exception:
        logger.exception("Hourly collection FAILED for %s", target_hour.isoformat())
