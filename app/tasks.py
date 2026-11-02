import asyncio
import csv
import os
from datetime import datetime, timedelta, timezone

import boto3
from sqlalchemy import delete, select

from app.database import async_session
from app.models.log_record import LogRecord
from app.worker import celery_app


def _s3_client():
    return boto3.client(
        "s3",
        endpoint_url=os.getenv("S3_ENDPOINT", "http://localhost:9000"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "minioadmin"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "minioadmin"),
        region_name=os.getenv("AWS_REGION", "us-east-1"),
    )


async def _archive() -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    async with async_session() as session:
        result = await session.execute(
            select(LogRecord).where(LogRecord.timestamp < cutoff)
        )
        records = result.scalars().all()
        if not records:
            return 0

        filename = f"/tmp/archive_{cutoff:%Y%m%d%H%M%S}.csv"
        bucket = os.getenv("S3_BUCKET", "log-archives")
        object_name = os.path.basename(filename)
        try:
            with open(filename, "w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow(["id", "service", "severity", "message", "timestamp"])
                for record in records:
                    writer.writerow(
                        [
                            str(record.id),
                            record.service,
                            record.severity.value,
                            record.message,
                            record.timestamp.isoformat(),
                        ]
                    )

            client = _s3_client()
            await asyncio.to_thread(client.upload_file, filename, bucket, object_name)
            await session.execute(delete(LogRecord).where(LogRecord.timestamp < cutoff))
            await session.commit()
            return len(records)
        finally:
            if os.path.exists(filename):
                os.remove(filename)


@celery_app.task(
    bind=True,
    max_retries=3,
    name="app.tasks.archive_and_cleanup_old_logs",
)
def archive_and_cleanup_old_logs(self) -> dict[str, int | str]:
    try:
        count = asyncio.run(_archive())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60) from exc
    return {"status": "success", "archived_and_deleted_rows": count}
