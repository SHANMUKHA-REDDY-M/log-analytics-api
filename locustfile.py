import random

from locust import HttpUser, between, task

SERVICES = [
    "auth-api",
    "billing-service",
    "frontend-app",
    "inventory-db",
    "notification-worker",
]
SEVERITIES = ["DEBUG", "INFO", "WARN", "ERROR", "FATAL"]


class LogAnalyticsUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def ingest_log(self) -> None:
        payload = {
            "service": random.choice(SERVICES),
            "severity": random.choice(SEVERITIES),
            "message": "Simulated high-throughput log message",
            "meta_payload": {
                "request_id": f"req_{random.randint(1000, 9999)}",
            },
        }
        self.client.post("/api/v1/logs/", json=payload, name="POST /logs")

    @task(2)
    def search_logs(self) -> None:
        severity = random.choice(SEVERITIES)
        service = random.choice(SERVICES)
        self.client.get(
            "/api/v1/logs/",
            params={
                "severity": severity,
                "service": service,
                "size": 50,
            },
            name="GET /logs (Search)",
        )

    @task(1)
    def get_stats(self) -> None:
        self.client.get("/api/v1/logs/stats", name="GET /logs/stats")
