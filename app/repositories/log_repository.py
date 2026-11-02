from datetime import datetime
from typing import TypeAlias

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.log_record import LogRecord, LogSeverity
from app.schemas.log import LogCreate

LogResults: TypeAlias = tuple[list[LogRecord], int]


class LogRepository:
    async def create(self, db: AsyncSession, log_data: LogCreate) -> LogRecord:
        db_log = LogRecord(
            service=log_data.service,
            severity=log_data.severity,
            message=log_data.message,
            timestamp=log_data.timestamp,
            meta_payload=log_data.meta_payload,
        )
        db.add(db_log)
        await db.commit()
        await db.refresh(db_log)
        return db_log

    async def get_logs(
        self,
        db: AsyncSession,
        severity: LogSeverity | None = None,
        service: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> LogResults:
        query = select(LogRecord)

        if severity is not None:
            query = query.where(LogRecord.severity == severity)
        if service is not None:
            query = query.where(LogRecord.service == service)
        if start_time is not None:
            query = query.where(LogRecord.timestamp >= start_time)
        if end_time is not None:
            query = query.where(LogRecord.timestamp <= end_time)

        count_query = select(func.count()).select_from(query.subquery())
        total_count = (await db.execute(count_query)).scalar_one()

        query = query.order_by(LogRecord.timestamp.desc()).limit(limit).offset(offset)
        logs = (await db.execute(query)).scalars().all()

        return logs, total_count

    async def get_stats_by_severity(
        self,
        db: AsyncSession,
        service: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[tuple[LogSeverity, int]]:
        query = select(
            LogRecord.severity,
            func.count(LogRecord.id).label("count"),
        )

        if service is not None:
            query = query.where(LogRecord.service == service)
        if start_time is not None:
            query = query.where(LogRecord.timestamp >= start_time)
        if end_time is not None:
            query = query.where(LogRecord.timestamp <= end_time)

        query = query.group_by(LogRecord.severity)
        result = await db.execute(query)
        return [(row.severity, row.count) for row in result.all()]

    async def get_logs_by_user(
        self,
        db: AsyncSession,
        user_id: int,
    ) -> list[LogRecord]:
        query = select(LogRecord).where(
            LogRecord.meta_payload.contains({"user_id": user_id})
        )
        result = await db.execute(query)
        return list(result.scalars().all())
