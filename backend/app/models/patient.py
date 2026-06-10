import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, Date, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    mrn: Mapped[str | None] = mapped_column(String(50))
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    date_of_birth: Mapped[datetime] = mapped_column(Date, nullable=False)
    gender: Mapped[str | None] = mapped_column(String(20))
    phone: Mapped[str | None] = mapped_column(String(20))
    insurance_provider: Mapped[str | None] = mapped_column(String(255))
    insurance_plan_name: Mapped[str | None] = mapped_column(String(255))
    insurance_member_id: Mapped[str | None] = mapped_column(String(100))
    code_status: Mapped[str] = mapped_column(String(50), default="FULL_CODE")  # FULL_CODE, DNR, DNI, DNR_DNI, COMFORT_CARE
    allergies: Mapped[dict | None] = mapped_column(JSON, default=list)
    primary_language: Mapped[str] = mapped_column(String(50), default="English")
    interpreter_needed: Mapped[bool] = mapped_column(Boolean, default=False)
    # Clinical data for current encounter
    vitals: Mapped[dict | None] = mapped_column(JSON, default=dict)
    active_conditions: Mapped[list | None] = mapped_column(JSON, default=list)
    current_medications: Mapped[list | None] = mapped_column(JSON, default=list)
    lab_results: Mapped[list | None] = mapped_column(JSON, default=list)
    imaging_results: Mapped[list | None] = mapped_column(JSON, default=list)
    medical_history: Mapped[list | None] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def age(self) -> int:
        today = datetime.now(timezone.utc).date()
        dob = self.date_of_birth
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
