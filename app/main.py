import time

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app
from starlette.requests import Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1 import logs
from app.core.config import settings
from app.core.metrics import REQUEST_COUNT, REQUEST_LATENCY
from app.database import get_db

from app.core.telemetry import setup_api_telemetry

app = FastAPI(title="Log Analytics and Search API")
setup_api_telemetry(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/metrics", make_asgi_app())


@app.middleware("http")
async def prometheus_metrics_middleware(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    endpoint = request.scope.get("route")
    endpoint_name = endpoint.path if endpoint else request.url.path
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=endpoint_name,
        http_status=response.status_code,
    ).inc()
    REQUEST_LATENCY.labels(
        method=request.method,
        endpoint=endpoint_name,
    ).observe(time.perf_counter() - start_time)
    return response


app.include_router(logs.router, prefix="/api/v1/logs", tags=["Logs"])


@app.get("/api/v1/health")
async def health_check(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "unhealthy",
                "database": "disconnected",
            },
        ) from exc

    return {
        "status": "healthy",
        "database": "connected",
    }


@app.get("/health/live")
async def liveness_check() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/health/ready")
async def readiness_check(
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    return await health_check(db)
