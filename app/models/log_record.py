import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LogSeverity(str, enum.Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    FATAL = "FATAL"


class LogRecord(Base):
    __tablename__ = "logs"
    __table_args__ = (
        Index(
            "ix_logs_meta_payload_gin",
            "meta_payload",
            postgresql_using="gin",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    service: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    severity: Mapped[LogSeverity] = mapped_column(
        Enum(LogSeverity),
        index=True,
        nullable=False,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        index=True,
        server_default=text("now()"),
    )
    meta_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
