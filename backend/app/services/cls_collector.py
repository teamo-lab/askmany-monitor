"""CLS data collection service for forbidden word monitoring."""

import asyncio
import json
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ForbiddenEvent, HourlyStat

logger = logging.getLogger(__name__)


def get_category(risk_description: str | None) -> str:
    if not risk_description:
        return "other"
    mapping = [
        ("辱骂", "abuse"),
        ("色情", "porn"),
        ("涉政", "politics"),
        ("违禁", "ban"),
        ("广告", "ad"),
        ("暴力", "violence"),
    ]
    for prefix, category in mapping:
        if risk_description.startswith(prefix):
            return category
    return "other"


class CLSCollector:
    def __init__(self, secret_id: str, secret_key: str, region: str, topic_id: str):
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.region = region
        self.topic_id = topic_id

    @staticmethod
    def parse_hourly_stats(records: list[str]) -> list[dict]:
        results = []
        for r in records:
            data = json.loads(r)
            results.append({
                "hour_slot": data["hour_slot"],
                "blocked_count": int(data["blocked_count"]),
                "user_uv": int(data["user_uv"]),
                "conv_uv": int(data["conv_uv"]),
            })
        return results

    @staticmethod
    def parse_total_requests(records: list[str]) -> dict[str, int]:
        result = {}
        for r in records:
            data = json.loads(r)
            result[data["hour_slot"]] = int(data["total_requests"])
        return result

    @staticmethod
    def parse_category_distribution(records: list[str]) -> dict[str, dict]:
        result: dict[str, dict] = {}
        for r in records:
            data = json.loads(r)
            slot = data["hour_slot"]
            if slot not in result:
                result[slot] = {}
            result[slot][data["category"]] = int(data["cnt"])
        return result

    @staticmethod
    def parse_direction_distribution(records: list[str]) -> dict[str, dict]:
        result: dict[str, dict] = {}
        for r in records:
            data = json.loads(r)
            slot = data["hour_slot"]
            if slot not in result:
                result[slot] = {}
            result[slot][data["direction"]] = int(data["cnt"])
        return result

    @staticmethod
    def parse_events(records: list[str]) -> list[dict]:
        results = []
        for r in records:
            data = json.loads(r)
            text = data.get("text", "")
            results.append({
                "event_time": data.get("event_time", ""),
                "direction": data.get("event_id") or "unknown",
                "risk_level": data.get("risk_level") or "UNKNOWN",
                "risk_description": data.get("risk_description", ""),
                "category": get_category(data.get("risk_description")),
                "source": data.get("source") or "unknown",
                "username": data.get("username"),
                "conv_id": data.get("conv_id") or "unknown",
                "text_preview": text[:200] if text else None,
                "cls_log_id": data.get("cls_log_id"),
            })
        return results

    async def _query_cls(self, sql: str, from_ts: int, to_ts: int) -> list[str]:
        """Query CLS API. Runs SDK in thread since it's synchronous."""
        from tencentcloud.common import credential
        from tencentcloud.cls.v20201016 import cls_client, models

        def _do_query():
            cred = credential.Credential(self.secret_id, self.secret_key)
            client = cls_client.ClsClient(cred, self.region)
            req = models.SearchLogRequest()
            req.TopicId = self.topic_id
            req.From = from_ts
            req.To = to_ts
            req.Query = sql
            req.Limit = 1
            req.UseNewAnalysis = True
            resp = client.SearchLog(req)
            return resp.AnalysisRecords or []

        return await asyncio.to_thread(_do_query)

    async def collect_hourly(self, target_hour: datetime, session: AsyncSession):
        """Collect data for one hour and write to DB."""
        from_ts = int(target_hour.timestamp() * 1000)
        to_ts = from_ts + 3600 * 1000

        hour_slot = target_hour.strftime("%Y-%m-%d %H:00")

        # Run all CLS queries concurrently
        hourly_records, total_records, cat_records, dir_records, event_records = (
            await asyncio.gather(
                self._query_cls(
                    "* | SELECT DATE_FORMAT(CAST(event_time AS TIMESTAMP), '%Y-%m-%d %H:00') as hour_slot, "
                    "COUNT(*) as blocked_count, COUNT(DISTINCT username) as user_uv, "
                    "COUNT(DISTINCT conv_id) as conv_uv "
                    "WHERE event = 'forbidden_text_event' GROUP BY hour_slot ORDER BY hour_slot ASC",
                    from_ts, to_ts,
                ),
                self._query_cls(
                    "* | SELECT DATE_FORMAT(CAST(event_time AS TIMESTAMP), '%Y-%m-%d %H:00') as hour_slot, "
                    "COUNT(*) as total_requests "
                    "WHERE event = 'newapi_request' GROUP BY hour_slot ORDER BY hour_slot ASC",
                    from_ts, to_ts,
                ),
                self._query_cls(
                    "* | SELECT DATE_FORMAT(CAST(event_time AS TIMESTAMP), '%Y-%m-%d %H:00') as hour_slot, "
                    "CASE WHEN risk_description LIKE '辱骂%' THEN 'abuse' "
                    "WHEN risk_description LIKE '色情%' THEN 'porn' "
                    "WHEN risk_description LIKE '涉政%' THEN 'politics' "
                    "WHEN risk_description LIKE '违禁%' THEN 'ban' "
                    "WHEN risk_description LIKE '广告%' THEN 'ad' "
                    "WHEN risk_description LIKE '暴力%' THEN 'violence' "
                    "ELSE 'other' END as category, COUNT(*) as cnt "
                    "WHERE event = 'forbidden_text_event' GROUP BY hour_slot, category ORDER BY hour_slot ASC",
                    from_ts, to_ts,
                ),
                self._query_cls(
                    "* | SELECT DATE_FORMAT(CAST(event_time AS TIMESTAMP), '%Y-%m-%d %H:00') as hour_slot, "
                    "event_id as direction, COUNT(*) as cnt "
                    "WHERE event = 'forbidden_text_event' GROUP BY hour_slot, event_id ORDER BY hour_slot ASC",
                    from_ts, to_ts,
                ),
                self._query_cls(
                    "* | SELECT event_time, event_id, risk_level, risk_description, source, username, conv_id, text "
                    "WHERE event = 'forbidden_text_event' ORDER BY event_time ASC LIMIT 10000",
                    from_ts, to_ts,
                ),
            )
        )

        # Parse responses
        hourly_stats = self.parse_hourly_stats(hourly_records)
        total_requests_map = self.parse_total_requests(total_records)
        categories_map = self.parse_category_distribution(cat_records)
        directions_map = self.parse_direction_distribution(dir_records)
        events = self.parse_events(event_records)

        # Write hourly_stats (upsert)
        for stat in hourly_stats:
            slot = stat["hour_slot"]
            total = total_requests_map.get(slot, 0)
            blocked = stat["blocked_count"]
            rate = blocked / total if total > 0 else 0

            ts = datetime.strptime(slot, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)

            existing = await session.execute(
                select(HourlyStat).where(HourlyStat.timestamp_utc == ts)
            )
            row = existing.scalar_one_or_none()

            if row:
                row.total_requests = total
                row.blocked_count = blocked
                row.block_rate = round(rate, 4)
                row.user_uv = stat["user_uv"]
                row.conv_uv = stat["conv_uv"]
                row.categories = categories_map.get(slot, {})
                row.directions = directions_map.get(slot, {})
            else:
                row = HourlyStat(
                    timestamp_utc=ts,
                    weekday=ts.weekday(),
                    hour_utc=ts.hour,
                    total_requests=total,
                    blocked_count=blocked,
                    block_rate=round(rate, 4),
                    user_uv=stat["user_uv"],
                    conv_uv=stat["conv_uv"],
                    categories=categories_map.get(slot, {}),
                    directions=directions_map.get(slot, {}),
                )
                session.add(row)

        # Write forbidden_events (with dedup by cls_log_id)
        for evt in events:
            cls_log_id = evt.get("cls_log_id")
            if cls_log_id:
                existing = await session.execute(
                    select(ForbiddenEvent).where(ForbiddenEvent.cls_log_id == cls_log_id)
                )
                if existing.scalar_one_or_none():
                    continue

            event = ForbiddenEvent(
                event_time=datetime.strptime(
                    evt["event_time"].split(".")[0], "%Y-%m-%d %H:%M:%S"
                ).replace(tzinfo=timezone.utc),
                username=evt["username"],
                conv_id=evt["conv_id"],
                direction=evt["direction"],
                risk_level=evt["risk_level"],
                risk_description=evt["risk_description"],
                category=evt["category"],
                source=evt["source"],
                text_preview=evt["text_preview"],
                cls_log_id=cls_log_id,
            )
            session.add(event)

        await session.commit()
        logger.info("Collected data for %s: %d blocked, %d events",
                     hour_slot, sum(s["blocked_count"] for s in hourly_stats), len(events))
