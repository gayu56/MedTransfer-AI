import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Float, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TransportRequest(Base):
    __tablename__ = "transport_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    transfer_id: Mapped[str] = mapped_column(String(36), ForeignKey("transfer_requests.id"), nullable=False)
    transport_level: Mapped[str] = mapped_column(String(10), nullable=False)  # BLS, ALS, CCT, AIR
    transport_provider_name: Mapped[str | None] = mapped_column(String(255))
    pickup_facility_id: Mapped[str] = mapped_column(String(36), ForeignKey("facilities.id"), nullable=False)
    dropoff_facility_id: Mapped[str] = mapped_column(String(36), ForeignKey("facilities.id"), nullable=False)

    status: Mapped[str] = mapped_column(String(30), nullable=False, default="REQUESTED")
    # REQUESTED, DISPATCHED, EN_ROUTE_PICKUP, ON_SCENE, TRANSPORTING, ARRIVED, COMPLETED, CANCELLED

    estimated_pickup_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actual_pickup_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    estimated_arrival_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actual_arrival_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    current_gps_lat: Mapped[float | None] = mapped_column(Float)
    current_gps_lng: Mapped[float | None] = mapped_column(Float)
    crew_lead_name: Mapped[str | None] = mapped_column(String(255))
    crew_lead_phone: Mapped[str | None] = mapped_column(String(20))
    crew_notes: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    transfer = relationship("TransferRequest", back_populates="transport_request")
    pickup_facility = relationship("Facility", foreign_keys=[pickup_facility_id])
    dropoff_facility = relationship("Facility", foreign_keys=[dropoff_facility_id])
