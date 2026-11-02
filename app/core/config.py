from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://admin:adminpassword@localhost:5432/logsdb"
    REDIS_URL: str = "redis://localhost:6379/0"
    API_KEYS: str = "service-auth-xyz,service-billing-abc"
    CELERY_BROKER_URL: str = "amqp://admin:adminpassword@localhost:5672//"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"
    S3_ENDPOINT: str = "http://localhost:9000"
    S3_BUCKET: str = "log-archives"
    AWS_ACCESS_KEY_ID: str = "minioadmin"
    AWS_SECRET_ACCESS_KEY: str = "minioadmin"
    AWS_REGION: str = "us-east-1"
    OTEL_EXPORTER_OTLP_ENDPOINT: str | None = None
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3001"
    RATE_LIMIT_REQUESTS: int = 500
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
