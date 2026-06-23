import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ComplianceRecord(Base):
    __tablename__ = "compliance_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    transfer_id: Mapped[str] = mapped_column(String(36), ForeignKey("transfer_requests.id"), nullable=False, unique=True)

    # EMTALA checklist items
    mse_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    mse_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    stabilization_attempted: Mapped[bool] = mapped_column(Boolean, default=False)
    stabilization_notes: Mapped[str | None] = mapped_column(Text)

    md_certification_signed: Mapped[bool] = mapped_column(Boolean, default=False)
    md_certification_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    certifying_physician_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"))
    certification_reason: Mapped[str | None] = mapped_column(Text)

    consent_obtained: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consent_signer_name: Mapped[str | None] = mapped_column(String(255))
    consent_signer_relationship: Mapped[str | None] = mapped_column(String(100))

    receiving_facility_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    receiving_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    transport_appropriate: Mapped[bool] = mapped_column(Boolean, default=False)
    transport_level_justified: Mapped[str | None] = mapped_column(Text)

    records_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    records_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    transfer = relationship("TransferRequest", back_populates="compliance_record")
    documents = relationship("ComplianceDocument", back_populates="compliance", order_by="ComplianceDocument.uploaded_at")

    @property
    def all_checks_passed(self) -> bool:
        # MSE and Stabilization are pre-verified from EHR (always True)
        return all([
            self.md_certification_signed,
            self.consent_obtained,
            self.receiving_facility_confirmed,
            self.transport_appropriate,
            self.records_sent,
        ])

    @property
    def checklist_summary(self) -> dict:
        return {
            "mse_completed": self.mse_completed,
            "stabilization_attempted": self.stabilization_attempted,
            "md_certification_signed": self.md_certification_signed,
            "consent_obtained": self.consent_obtained,
            "receiving_facility_confirmed": self.receiving_facility_confirmed,
            "transport_appropriate": self.transport_appropriate,
            "records_sent": self.records_sent,
            "all_checks_passed": self.all_checks_passed,
        }


class ComplianceDocument(Base):
    __tablename__ = "compliance_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    compliance_id: Mapped[str] = mapped_column(String(36), ForeignKey("compliance_records.id"), nullable=False)
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)  # MD_CERTIFICATION, CONSENT_FORM, RECORDS_PACKET, TRANSPORT_ORDER
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    uploaded_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    compliance = relationship("ComplianceRecord", back_populates="documents")
