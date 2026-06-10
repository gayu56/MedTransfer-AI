import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)  # NURSE_PRACTITIONER, PHYSICIAN, TRANSFER_COORDINATOR, EMS_CREW, ADMINISTRATOR
    phone: Mapped[str | None] = mapped_column(String(20))
    npi: Mapped[str | None] = mapped_column(String(10))
    specialty: Mapped[str | None] = mapped_column(String(100))
    organization_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("organizations.id"))
    facility_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("facilities.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
