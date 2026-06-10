from datetime import datetime
from pydantic import BaseModel

from app.schemas.patient import PatientResponse


class TransferCreate(BaseModel):
    patient_id: str
    urgency: str  # EMERGENT, URGENT, ROUTINE
    reason_for_transfer: str
    requested_specialty: str | None = None
    requested_unit_type: str | None = None
    preferred_facility_id: str | None = None
    additional_notes: str | None = None
    clinical_summary_id: str | None = None


class TransferAccept(BaseModel):
    accepting_physician_notes: str | None = None
    assigned_unit: str | None = None
    assigned_bed: str | None = None


class TransferDecline(BaseModel):
    reason: str  # NO_BED_AVAILABLE, NO_SPECIALIST_AVAILABLE, etc.
    notes: str | None = None
    auto_reroute: bool = True


class TransferStatusUpdate(BaseModel):
    status: str
    notes: str | None = None


class FacilitySummary(BaseModel):
    id: str
    name: str
    phone: str | None = None
    city: str | None = None
    state: str | None = None

    class Config:
        from_attributes = True


class ClinicalSummaryResponse(BaseModel):
    id: str
    situation: str
    background: str
    assessment: str
    recommendation: str
    generated_by_ai: bool = False
    version: int = 1
    reviewed_at: datetime | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class ComplianceResponse(BaseModel):
    id: str
    mse_completed: bool = False
    stabilization_attempted: bool = False
    md_certification_signed: bool = False
    consent_obtained: bool = False
    receiving_facility_confirmed: bool = False
    transport_appropriate: bool = False
    records_sent: bool = False
    all_checks_passed: bool = False

    class Config:
        from_attributes = True


class FacilityMatchResponse(BaseModel):
    rank: int
    facility_id: str
    facility_name: str | None = None
    facility_city: str | None = None
    facility_state: str | None = None
    overall_score: float
    specialty_score: float = 0
    bed_availability_score: float = 0
    distance_score: float = 0
    insurance_score: float = 0
    distance_miles: float | None = None
    estimated_transport_min: int | None = None
    status: str = "SUGGESTED"

    class Config:
        from_attributes = True


class TimelineEvent(BaseModel):
    id: str
    event_type: str
    event_description: str
    triggered_by_system: bool = False
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class TransportResponse(BaseModel):
    id: str
    transport_level: str
    transport_provider_name: str | None = None
    status: str = "REQUESTED"
    estimated_pickup_at: datetime | None = None
    actual_pickup_at: datetime | None = None
    estimated_arrival_at: datetime | None = None
    actual_arrival_at: datetime | None = None

    class Config:
        from_attributes = True


class TransferResponse(BaseModel):
    id: str
    transfer_number: str
    status: str
    urgency: str
    reason_for_transfer: str
    requested_specialty: str | None = None
    requested_unit_type: str | None = None
    additional_notes: str | None = None
    patient: PatientResponse | None = None
    sending_facility: FacilitySummary | None = None
    receiving_facility: FacilitySummary | None = None
    clinical_summary: ClinicalSummaryResponse | None = None
    compliance_record: ComplianceResponse | None = None
    transport_request: TransportResponse | None = None
    facility_matches: list[FacilityMatchResponse] = []
    timeline: list[TimelineEvent] = []
    initiated_at: datetime | None = None
    accepted_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class TransferListResponse(BaseModel):
    data: list[TransferResponse]
    total_count: int
