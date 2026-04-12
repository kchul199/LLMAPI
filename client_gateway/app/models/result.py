from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AnalysisResultRecord(Base):
    __tablename__ = "client_analysis_result"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[int] = mapped_column(Integer, ForeignKey("client_analysis_request.id", ondelete="CASCADE"), unique=True)

    result_status: Mapped[str] = mapped_column(Enum("SUCCESS", "FAIL", name="result_status_enum"), default="SUCCESS", nullable=False)

    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    sentiment: Mapped[str | None] = mapped_column(String(32), nullable=True)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    result_json: Mapped[dict] = mapped_column(JSON, nullable=False)

    usage_total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    usage_latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    llm_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_fallback: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    prompt_version_applied: Mapped[str | None] = mapped_column(String(32), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=datetime.utcnow)

    request = relationship("AnalysisRequestRecord", back_populates="result")
