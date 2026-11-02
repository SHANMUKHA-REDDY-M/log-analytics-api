import asyncio
import os
import random
import sys
from datetime import datetime, timedelta, timezone

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from faker import Faker

from app.database import async_session
from app.models.log_record import LogRecord, LogSeverity

fake = Faker()

SERVICES = [
    "auth-api",
    "billing-service",
    "frontend-app",
    "inventory-db",
    "notification-worker",
]
SEVERITIES = list(LogSeverity)


def generate_mock_log() -> LogRecord:
    days_ago = random.randint(0, 30)
    random_time = datetime.now(timezone.utc) - timedelta(
        days=days_ago,
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
    )

    return LogRecord(
        service=random.choice(SERVICES),
        severity=random.choice(SEVERITIES),
        message=fake.sentence(nb_words=10),
        timestamp=random_time,
        meta_payload={
            "ip_address": fake.ipv4(),
            "user_id": random.randint(1, 10000) if random.random() > 0.5 else None,
            "latency_ms": random.randint(10, 2500),
        },
    )


async def seed_database(total_records: int = 100_000, batch_size: int = 5_000) -> None:
    print(f"Starting database seed for {total_records} records...")

    async with async_session() as session:
        records: list[LogRecord] = []
        for i in range(1, total_records + 1):
            records.append(generate_mock_log())

            if i % batch_size == 0:
                session.add_all(records)
                await session.commit()
                print(f"Inserted {i} / {total_records} logs...")
                records = []

        if records:
            session.add_all(records)
            await session.commit()
            print(f"Inserted final {len(records)} logs.")

    print("Seeding complete! You can now test the API performance.")


if __name__ == "__main__":
    asyncio.run(seed_database())
