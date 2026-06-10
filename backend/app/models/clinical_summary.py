import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, Integer, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ClinicalSummary(Base):
    __tablename__ = "clinical_summaries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    transfer_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("transfer_requests.id"), nullable=True)
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)

    # SBAR sections
    situation: Mapped[str] = mapped_column(Text, nullable=False)
    background: Mapped[str] = mapped_column(Text, nullable=False)
    assessment: Mapped[str] = mapped_column(Text, nullable=False)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)

    # Structured clinical data
    vitals: Mapped[dict | None] = mapped_column(JSON, default=dict)
    active_conditions: Mapped[list | None] = mapped_column(JSON, default=list)
    current_medications: Mapped[list | None] = mapped_column(JSON, default=list)
    lab_results: Mapped[list | None] = mapped_column(JSON, default=list)
    imaging_results: Mapped[list | None] = mapped_column(JSON, default=list)

    additional_notes: Mapped[str | None] = mapped_column(Text)
    generated_by_ai: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_model_version: Mapped[str | None] = mapped_column(String(50))
    reviewed_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    transfer = relationship("TransferRequest", back_populates="clinical_summary")
