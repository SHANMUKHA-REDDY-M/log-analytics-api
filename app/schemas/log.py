from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.log_record import LogSeverity


class LogCreate(BaseModel):
    service: str = Field(..., max_length=100, description="Name of the microservice")
    severity: LogSeverity
    message: str = Field(..., description="The actual log message")
    timestamp: datetime | None = Field(
        default=None,
        description="UTC timestamp. Defaults to server time if omitted.",
    )
    meta_payload: dict[str, Any] | None = Field(
        default=None,
        description="Arbitrary JSON metadata",
    )


class LogResponse(LogCreate):
    id: UUID
    message: str
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginationMeta(BaseModel):
    total: int
    page: int
    size: int


class PaginatedLogResponse(BaseModel):
    data: list[LogResponse]
    meta: PaginationMeta


class LogStatsResponse(BaseModel):
    severity: LogSeverity
    count: int
