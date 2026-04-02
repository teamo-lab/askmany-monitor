"""Backfill historical CLS data into PostgreSQL.

Usage:
    python -m scripts.backfill --from 2026-03-31 --to 2026-04-02

Pulls data hour-by-hour from CLS and writes to hourly_stats + forbidden_events.
Idempotent: safe to re-run (uses upsert for stats, dedup by cls_log_id for events).
"""

import argparse
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from app.config import settings
from app.database import AsyncSessionLocal, engine
from app.services.cls_collector import CLSCollector

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def backfill(from_date: str, to_date: str):
    from_dt = datetime.strptime(from_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    to_dt = datetime.strptime(to_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)

    # If to_date is today, only go up to current hour
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    end_dt = min(to_dt + timedelta(days=1), now)

    collector = CLSCollector(
        secret_id=settings.tencent_secret_id,
        secret_key=settings.tencent_secret_key,
        region=settings.cls_region,
        topic_id=settings.cls_topic_id,
    )

    current = from_dt
    total_hours = int((end_dt - from_dt).total_seconds() / 3600)
    completed = 0

    while current < end_dt:
        logger.info("Backfilling %s (%d/%d)", current.isoformat(), completed + 1, total_hours)
        try:
            async with AsyncSessionLocal() as session:
                await collector.collect_hourly(current, session)
            logger.info("OK: %s", current.isoformat())
        except Exception:
            logger.exception("FAILED: %s", current.isoformat())

        current += timedelta(hours=1)
        completed += 1

        # Rate limit: small delay between CLS API calls
        await asyncio.sleep(1)

    logger.info("Backfill complete: %d hours processed", completed)


def main():
    parser = argparse.ArgumentParser(description="Backfill CLS data")
    parser.add_argument("--from-date", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--to-date", required=True, help="End date inclusive (YYYY-MM-DD)")
    args = parser.parse_args()

    asyncio.run(backfill(args.from_date, args.to_date))


if __name__ == "__main__":
    main()
