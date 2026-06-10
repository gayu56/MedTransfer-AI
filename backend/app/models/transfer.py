import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, Float, Integer, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TransferRequest(Base):
    __tablename__ = "transfer_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    transfer_number: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id"), nullable=False)
    sending_facility_id: Mapped[str] = mapped_column(String(36), ForeignKey("facilities.id"), nullable=False)
    receiving_facility_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("facilities.id"))
    initiated_by_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    accepted_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"))

    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    urgency: Mapped[str] = mapped_column(String(20), nullable=False)  # EMERGENT, URGENT, ROUTINE
    reason_for_transfer: Mapped[str] = mapped_column(Text, nullable=False)
    requested_specialty: Mapped[str | None] = mapped_column(String(100))
    requested_unit_type: Mapped[str | None] = mapped_column(String(50))
    additional_notes: Mapped[str | None] = mapped_column(Text)

    decline_reason: Mapped[str | None] = mapped_column(Text)
    cancellation_reason: Mapped[str | None] = mapped_column(Text)

    # Timestamps for SLA tracking
    initiated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_facility_contacted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    transport_dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    patient_departed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    patient_arrived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    patient = relationship("Patient", foreign_keys=[patient_id])
    sending_facility = relationship("Facility", foreign_keys=[sending_facility_id])
    receiving_facility = relationship("Facility", foreign_keys=[receiving_facility_id])
    initiated_by = relationship("User", foreign_keys=[initiated_by_user_id])
    accepted_by = relationship("User", foreign_keys=[accepted_by_user_id])
    clinical_summary = relationship("ClinicalSummary", back_populates="transfer", uselist=False)
    compliance_record = relationship("ComplianceRecord", back_populates="transfer", uselist=False)
    transport_request = relationship("TransportRequest", back_populates="transfer", uselist=False)
    facility_matches = relationship("FacilityMatch", back_populates="transfer", order_by="FacilityMatch.rank")
    timeline = relationship("TransferTimeline", back_populates="transfer", order_by="TransferTimeline.created_at")


class FacilityMatch(Base):
    __tablename__ = "facility_matches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    transfer_id: Mapped[str] = mapped_column(String(36), ForeignKey("transfer_requests.id"), nullable=False)
    facility_id: Mapped[str] = mapped_column(String(36), ForeignKey("facilities.id"), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    specialty_score: Mapped[float] = mapped_column(Float, default=0)
    bed_availability_score: Mapped[float] = mapped_column(Float, default=0)
    distance_score: Mapped[float] = mapped_column(Float, default=0)
    insurance_score: Mapped[float] = mapped_column(Float, default=0)
    historical_score: Mapped[float] = mapped_column(Float, default=0)
    distance_miles: Mapped[float | None] = mapped_column(Float)
    estimated_transport_min: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="SUGGESTED")  # SUGGESTED, SENT, ACCEPTED, DECLINED, SKIPPED
    declined_reason: Mapped[str | None] = mapped_column(Text)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    transfer = relationship("TransferRequest", back_populates="facility_matches")
    facility = relationship("Facility")


class TransferTimeline(Base):
    __tablename__ = "transfer_timeline"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    transfer_id: Mapped[str] = mapped_column(String(36), ForeignKey("transfer_requests.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    event_description: Mapped[str] = mapped_column(Text, nullable=False)
    triggered_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"))
    triggered_by_system: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    transfer = relationship("TransferRequest", back_populates="timeline")
