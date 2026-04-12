from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String, Text, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AnalysisRequestRecord(Base):
    __tablename__ = "client_analysis_request"
    __table_args__ = (
        UniqueConstraint("source_system", "client_request_id", name="uk_source_client_request"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_uid: Mapped[str] = mapped_column(String(36), unique=True, index=True)

    source_system: Mapped[str] = mapped_column(String(64), nullable=False)
    client_request_id: Mapped[str] = mapped_column(String(100), nullable=False)
    trace_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    mode: Mapped[str] = mapped_column(Enum("sync", "async", name="mode_enum"), nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("RECEIVED", "QUEUED", "PROCESSING", "COMPLETED", "FAILED", "TIMEOUT", name="request_status_enum"),
        nullable=False,
        default="RECEIVED",
    )

    text_masked: Mapped[str] = mapped_column(Text, nullable=False)
    text_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    tasks: Mapped[list] = mapped_column(JSON, nullable=False)
    target_speakers: Mapped[str] = mapped_column(
        Enum("agent", "customer", "both", name="target_speakers_enum"),
        nullable=False,
        default="both",
    )
    prompt_version: Mapped[str | None] = mapped_column(String(32), nullable=True)

    llmapi_request_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    llmapi_http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)

    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=datetime.utcnow)
    queued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=datetime.utcnow, onupdate=datetime.utcnow)

    result = relationship("AnalysisResultRecord", back_populates="request", uselist=False, cascade="all, delete-orphan")
    status_history = relationship("AnalysisStatusHistoryRecord", back_populates="request", cascade="all, delete-orphan")
