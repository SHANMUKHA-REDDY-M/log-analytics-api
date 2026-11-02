from httpx import ASGITransport, AsyncClient

from app.core.rate_limiter import SlidingWindowRateLimiter
from app.main import app

AUTH_HEADERS = {"X-API-Key": "service-auth-xyz"}


async def test_health_check_reports_database_connection(
    async_client: AsyncClient,
) -> None:
    response = await async_client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "database": "connected",
    }


async def test_ingest_log(async_client: AsyncClient) -> None:
    payload = {
        "service": "payment-gateway",
        "severity": "ERROR",
        "message": "Payment timeout from upstream provider",
        "meta_payload": {"transaction_id": "tx_999"},
    }

    response = await async_client.post(
        "/api/v1/logs/", json=payload, headers=AUTH_HEADERS
    )

    assert response.status_code == 201
    data = response.json()
    assert data["service"] == "payment-gateway"
    assert data["severity"] == "ERROR"
    assert "id" in data
    assert "timestamp" in data


async def test_search_logs_by_severity(async_client: AsyncClient) -> None:
    logs = [
        {"service": "app", "severity": "ERROR", "message": "Failed login"},
        {"service": "app", "severity": "INFO", "message": "User logged out"},
        {"service": "worker", "severity": "ERROR", "message": "Job crashed"},
    ]
    for log in logs:
        response = await async_client.post(
            "/api/v1/logs/", json=log, headers=AUTH_HEADERS
        )
        assert response.status_code == 201

    response = await async_client.get(
        "/api/v1/logs/?severity=ERROR", headers=AUTH_HEADERS
    )

    assert response.status_code == 200
    data = response.json()
    assert data["meta"]["total"] == 2
    assert len(data["data"]) == 2
    assert all(log["severity"] == "ERROR" for log in data["data"])


async def test_rate_limit_exceeded(monkeypatch) -> None:
    async def reject(self, identifier: str) -> None:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": "60"},
        )

    monkeypatch.setattr(SlidingWindowRateLimiter, "check", reject)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/api/v1/logs/",
            json={
                "service": "auth-service",
                "severity": "INFO",
                "message": "Rate limit test message",
            },
            headers=AUTH_HEADERS,
        )

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "60"


async def test_schema_validation_failure(async_client: AsyncClient) -> None:
    response = await async_client.post(
        "/api/v1/logs/",
        json={
            "service": "",
            "severity": "UNKNOWN_SEVERITY",
            "message": "",
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 422
