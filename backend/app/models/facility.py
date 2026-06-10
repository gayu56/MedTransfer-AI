import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, Float, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Facility(Base):
    __tablename__ = "facilities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    facility_type: Mapped[str] = mapped_column(String(50), nullable=False)  # HOSPITAL, TRAUMA_CENTER, URGENT_CARE, etc.
    trauma_level: Mapped[str | None] = mapped_column(String(10))  # LEVEL_1, LEVEL_2, LEVEL_3, NONE
    npi: Mapped[str | None] = mapped_column(String(10), unique=True)
    address_line1: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str | None] = mapped_column(String(100))
    state: Mapped[str | None] = mapped_column(String(2))
    zip_code: Mapped[str | None] = mapped_column(String(10))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    phone: Mapped[str | None] = mapped_column(String(20))
    transfer_center_phone: Mapped[str | None] = mapped_column(String(20))
    ehr_system: Mapped[str | None] = mapped_column(String(50))
    accepts_transfers: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    organization = relationship("Organization", back_populates="facilities")
    capabilities = relationship("FacilityCapability", back_populates="facility", cascade="all, delete-orphan")
    bed_availability = relationship("BedAvailability", back_populates="facility", cascade="all, delete-orphan")


class FacilityCapability(Base):
    __tablename__ = "facility_capabilities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    facility_id: Mapped[str] = mapped_column(String(36), ForeignKey("facilities.id"), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # SPECIALTY, SERVICE, UNIT_TYPE
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    available_24_7: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    facility = relationship("Facility", back_populates="capabilities")


class BedAvailability(Base):
    __tablename__ = "bed_availability"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    facility_id: Mapped[str] = mapped_column(String(36), ForeignKey("facilities.id"), nullable=False)
    unit_type: Mapped[str] = mapped_column(String(50), nullable=False)  # ICU, CCU, TELE, MED_SURG, etc.
    total_beds: Mapped[int] = mapped_column(Integer, default=0)
    occupied_beds: Mapped[int] = mapped_column(Integer, default=0)
    last_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    facility = relationship("Facility", back_populates="bed_availability")

    @property
    def available_beds(self) -> int:
        return max(0, self.total_beds - self.occupied_beds)
