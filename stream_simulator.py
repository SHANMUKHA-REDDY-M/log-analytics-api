"""Generate representative log traffic for local smoke testing."""

import argparse
import os
import random
import time
from collections.abc import Iterator
from typing import Any

import httpx

API_URL = os.getenv("API_URL", "http://localhost:8000/api/v1/logs/")
API_KEY = os.getenv("API_KEY", "service-auth-xyz")

SERVICES = (
    "auth-service",
    "payment-gateway",
    "order-processor",
    "inventory-api",
    "notification-worker",
)

MESSAGES = {
    "INFO": (
        "User session successfully validated.",
        "Database connection pool health check passed.",
        "Cache hit for product catalog query.",
        "Incoming webhook processed successfully.",
    ),
    "WARN": (
        "High memory utilization detected on worker node.",
        "Database query execution time exceeded threshold.",
        "Rate limit approaching threshold for client.",
        "Deprecated API endpoint invoked.",
    ),
    "ERROR": (
        "Failed to establish connection with upstream payment provider.",
        "Database deadlock encountered during transaction commit.",
        "Invalid token signature provided in authorization header.",
        "Timeout waiting for Redis cluster response.",
    ),
    "FATAL": (
        "Primary database replica out of sync; failing over.",
        "Out of memory exception thrown in background worker pool.",
        "Uncaught exception in main event loop.",
        "Storage volume capacity exceeded threshold.",
    ),
}


def generate_log_payload(rng: random.Random | None = None) -> dict[str, Any]:
    generator = rng or random
    severity = generator.choices(
        tuple(MESSAGES),
        weights=(60, 20, 15, 5),
        k=1,
    )[0]
    return {
        "service": generator.choice(SERVICES),
        "severity": severity,
        "message": generator.choice(MESSAGES[severity]),
        "meta_payload": {
            "environment": "local-enterprise",
            "region": os.getenv("AWS_REGION", "ap-south-1"),
            "pid": generator.randint(1000, 9999),
        },
    }


def payload_stream(
    rng: random.Random | None = None,
    count: int | None = None,
) -> Iterator[dict[str, Any]]:
    emitted = 0
    while count is None or emitted < count:
        yield generate_log_payload(rng)
        emitted += 1


def send_logs(
    client: httpx.Client,
    *,
    api_url: str,
    api_key: str,
    interval: tuple[float, float],
    count: int | None = None,
) -> None:
    headers = {"X-API-Key": api_key}
    for index, payload in enumerate(payload_stream(count=count)):
        try:
            response = client.post(api_url, json=payload, headers=headers)
        except httpx.RequestError as exc:
            print(f"Failed to reach API: {exc}")
            if count is not None:
                break
            time.sleep(random.uniform(*interval))
            continue
        if response.status_code == httpx.codes.CREATED:
            data = response.json()
            print(
                f"[{data['timestamp']}] ({data['severity']}) "
                f"[{data['service']}] -> Log ID {data['id']} ingested."
            )
        else:
            print(
                f"Failed to ingest log: HTTP {response.status_code} - {response.text}"
            )
        if count is None or index + 1 < count:
            time.sleep(random.uniform(*interval))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=None)
    parser.add_argument("--min-delay", type=float, default=0.2)
    parser.add_argument("--max-delay", type=float, default=1.0)
    parser.add_argument("--url", default=API_URL)
    parser.add_argument("--api-key", default=API_KEY)
    args = parser.parse_args()
    if args.count is not None and args.count < 1:
        parser.error("--count must be positive")
    if args.min_delay < 0 or args.max_delay < args.min_delay:
        parser.error("delay range is invalid")

    print(f"Starting log stream simulator -> targeting {args.url}")
    print("Press Ctrl+C to stop.")
    try:
        with httpx.Client(timeout=5.0) as client:
            send_logs(
                client,
                api_url=args.url,
                api_key=args.api_key,
                interval=(args.min_delay, args.max_delay),
                count=args.count,
            )
    except KeyboardInterrupt:
        print("\nLog stream simulator stopped by user.")


if __name__ == "__main__":
    main()
