import hashlib
import json
from datetime import datetime

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.metrics import LOGS_INGESTED
from app.models.log_record import LogRecord, LogSeverity
from app.repositories.log_repository import LogRepository
from app.schemas.log import (
    LogCreate,
    LogStatsResponse,
    PaginatedLogResponse,
    PaginationMeta,
)


class LogService:
    def __init__(self) -> None:
        self.log_repo = LogRepository()

    async def create_log(
        self,
        db: AsyncSession,
        redis: Redis,
        log_data: LogCreate,
    ) -> LogRecord:
        created_log = await self.log_repo.create(db, log_data)
        LOGS_INGESTED.labels(service_name=created_log.service).inc()
        await self._invalidate_stats_cache(redis)
        await redis.publish(
            "live_log_updates",
            json.dumps({"event": "new_log", "service": created_log.service}),
        )
        return created_log

    async def search_logs(
        self,
        db: AsyncSession,
        severity: LogSeverity | None,
        service: str | None,
        start_time: datetime | None,
        end_time: datetime | None,
        page: int,
        size: int,
    ) -> PaginatedLogResponse:
        offset = (page - 1) * size
        logs, total_count = await self.log_repo.get_logs(
            db=db,
            severity=severity,
            service=service,
            start_time=start_time,
            end_time=end_time,
            limit=size,
            offset=offset,
        )

        return PaginatedLogResponse(
            data=logs,
            meta=PaginationMeta(total=total_count, page=page, size=size),
        )

    async def get_severity_stats(
        self,
        db: AsyncSession,
        redis: Redis,
        service: str | None,
        start_time: datetime | None,
        end_time: datetime | None,
    ) -> list[LogStatsResponse]:
        cache_key = self._stats_cache_key(service, start_time, end_time)
        cached_data = await redis.get(cache_key)
        if cached_data is not None:
            return [LogStatsResponse(**item) for item in json.loads(cached_data)]

        raw_stats = await self.log_repo.get_stats_by_severity(
            db=db,
            service=service,
            start_time=start_time,
            end_time=end_time,
        )
        response = [
            LogStatsResponse(severity=severity, count=count)
            for severity, count in raw_stats
        ]
        await redis.setex(
            cache_key,
            60,
            json.dumps([item.model_dump(mode="json") for item in response]),
        )
        return response

    @staticmethod
    async def _invalidate_stats_cache(redis: Redis) -> None:
        keys = [key async for key in redis.scan_iter(match="stats:*")]
        if keys:
            await redis.delete(*keys)

    @staticmethod
    def _stats_cache_key(
        service: str | None,
        start_time: datetime | None,
        end_time: datetime | None,
    ) -> str:
        raw_key = f"stats:{service}:{start_time}:{end_time}"
        digest = hashlib.sha256(raw_key.encode()).hexdigest()
        return f"stats:{digest}"
