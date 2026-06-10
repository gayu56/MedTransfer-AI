import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Text, Integer, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CallLog(Base):
    __tablename__ = "call_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    transfer_id: Mapped[str] = mapped_column(String(36), ForeignKey("transfer_requests.id"), nullable=False)
    facility_id: Mapped[str] = mapped_column(String(36), ForeignKey("facilities.id"), nullable=False)
    called_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"))

    # Call details
    contact_name: Mapped[str | None] = mapped_column(String(200))
    contact_role: Mapped[str | None] = mapped_column(String(100))  # e.g. "Charge Nurse", "Transfer Center", "On-call Physician"
    phone_number: Mapped[str | None] = mapped_column(String(30))
    call_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    call_ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[int | None] = mapped_column(Integer)

    # Outcome
    outcome: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING")
    # PENDING, CONNECTED, ACCEPTED, DECLINED, NO_ANSWER, VOICEMAIL, CALLBACK_REQUESTED, TRANSFERRED_TO_MD
    decline_reason: Mapped[str | None] = mapped_column(Text)
    callback_time: Mapped[str | None] = mapped_column(String(100))
    accepting_physician: Mapped[str | None] = mapped_column(String(200))  # REQUIRED for ACCEPTED — real clinician who agreed
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=False)  # True if AI-simulated, not a real call
    human_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)  # Coordinator confirmed the outcome

    # Notes
    notes: Mapped[str | None] = mapped_column(Text)
    call_script_used: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    transfer = relationship("TransferRequest", backref="call_logs")
    facility = relationship("Facility")
    called_by = relationship("User")
