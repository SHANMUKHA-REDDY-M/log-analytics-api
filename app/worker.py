import os

from celery import Celery

from app.core.telemetry import setup_worker_telemetry

celery_app = Celery(
    "log_analytics_worker",
    broker=os.getenv("CELERY_BROKER_URL", "amqp://guest:guest@localhost:5672//"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1"),
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    enable_utc=True,
    timezone="UTC",
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
    worker_max_tasks_per_child=1000,
    beat_schedule={
        "archive-old-logs-daily": {
            "task": "app.tasks.archive_and_cleanup_old_logs",
            "schedule": 86400,
        }
    },
)
setup_worker_telemetry()
celery_app.autodiscover_tasks(["app"])
