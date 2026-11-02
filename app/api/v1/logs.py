from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import get_redis
from app.core.security import rate_limit, rate_limiter
from app.core.config import settings
from app.database import get_db
from app.models.log_record import LogSeverity
from app.schemas.log import (
    LogCreate,
    LogResponse,
    LogStatsResponse,
    PaginatedLogResponse,
)
from app.services.log_service import LogService

router = APIRouter()
log_service = LogService()


@router.post("/", response_model=LogResponse, status_code=status.HTTP_201_CREATED)
async def ingest_log(
    log_in: LogCreate,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    _api_key: str = Depends(rate_limit),
) -> LogResponse:
    """Ingest a single log record."""
    created_log = await log_service.create_log(db, redis, log_in)
    return created_log


@router.get("/", response_model=PaginatedLogResponse)
async def search_logs(
    severity: LogSeverity | None = Query(
        default=None,
        description="Filter by log severity",
    ),
    service: str | None = Query(
        default=None,
        description="Filter by microservice name",
    ),
    start_time: datetime | None = Query(
        default=None,
        description="Start boundary (UTC ISO format)",
    ),
    end_time: datetime | None = Query(
        default=None,
        description="End boundary (UTC ISO format)",
    ),
    page: int = Query(default=1, ge=1, description="Page number"),
    size: int = Query(
        default=50,
        ge=1,
        le=1000,
        description="Records per page",
    ),
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(rate_limit),
) -> PaginatedLogResponse:
    """Search and filter logs with pagination."""
    return await log_service.search_logs(
        db=db,
        severity=severity,
        service=service,
        start_time=start_time,
        end_time=end_time,
        page=page,
        size=size,
    )


@router.get("/stats", response_model=list[LogStatsResponse])
async def get_log_statistics(
    service: str | None = Query(
        default=None,
        description="Filter by microservice name",
    ),
    start_time: datetime | None = Query(
        default=None,
        description="Start boundary (UTC ISO format)",
    ),
    end_time: datetime | None = Query(
        default=None,
        description="End boundary (UTC ISO format)",
    ),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    _api_key: str = Depends(rate_limit),
) -> list[LogStatsResponse]:
    """Get aggregated counts of logs grouped by severity."""
    return await log_service.get_severity_stats(
        db=db,
        redis=redis,
        service=service,
        start_time=start_time,
        end_time=end_time,
    )


@router.websocket("/ws/stats")
async def websocket_stats(
    websocket: WebSocket,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> None:
    api_key = websocket.headers.get("x-api-key") or websocket.query_params.get(
        "api_key"
    )
    valid_keys = {key.strip() for key in settings.API_KEYS.split(",") if key.strip()}
    if api_key not in valid_keys:
        await websocket.close(code=1008, reason="Invalid API key")
        return

    try:
        await rate_limiter.check(api_key)
    except HTTPException:
        await websocket.close(code=1013, reason="Rate limit exceeded")
        return

    await websocket.accept()
    pubsub = redis.pubsub()
    await pubsub.subscribe("live_log_updates")
    try:
        initial_stats = await log_service.get_severity_stats(
            db, redis, None, None, None
        )
        await websocket.send_json(
            [stat.model_dump(mode="json") for stat in initial_stats]
        )
        while True:
            message = await pubsub.get_message(
                ignore_subscribe_messages=True, timeout=1.0
            )
            if message:
                await log_service._invalidate_stats_cache(redis)
                latest_stats = await log_service.get_severity_stats(
                    db, redis, None, None, None
                )
                await websocket.send_json(
                    [stat.model_dump(mode="json") for stat in latest_stats]
                )
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe("live_log_updates")
        await pubsub.close()
