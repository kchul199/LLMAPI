from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AnalysisStatusHistoryRecord(Base):
    __tablename__ = "client_analysis_status_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[int] = mapped_column(Integer, ForeignKey("client_analysis_request.id", ondelete="CASCADE"), nullable=False)

    prev_status: Mapped[str | None] = mapped_column(
        Enum("RECEIVED", "QUEUED", "PROCESSING", "COMPLETED", "FAILED", "TIMEOUT", name="status_history_prev_enum"),
        nullable=True,
    )
    new_status: Mapped[str] = mapped_column(
        Enum("RECEIVED", "QUEUED", "PROCESSING", "COMPLETED", "FAILED", "TIMEOUT", name="status_history_new_enum"),
        nullable=False,
    )

    reason_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reason_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    actor: Mapped[str] = mapped_column(String(32), nullable=False, default="system")
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=datetime.utcnow)

    request = relationship("AnalysisRequestRecord", back_populates="status_history")
