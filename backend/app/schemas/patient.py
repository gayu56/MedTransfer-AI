from datetime import date, datetime
from pydantic import BaseModel


class VitalsData(BaseModel):
    bp_systolic: int | None = None
    bp_diastolic: int | None = None
    heart_rate: int | None = None
    respiratory_rate: int | None = None
    spo2: int | None = None
    temperature: float | None = None
    temperature_unit: str = "F"
    pain_scale: int | None = None
    gcs_total: int | None = None
    oxygen_delivery: str | None = None
    oxygen_flow_rate: str | None = None
    recorded_at: str | None = None


class ConditionData(BaseModel):
    code: str | None = None
    display: str
    coding_system: str = "ICD-10-CM"
    clinical_status: str = "active"
    severity: str | None = None
    onset_date: str | None = None


class MedicationData(BaseModel):
    name: str
    dose: str | None = None
    dose_unit: str | None = None
    route: str | None = None
    frequency: str | None = None


class LabResultData(BaseModel):
    name: str
    value: str
    unit: str | None = None
    reference_range_text: str | None = None
    interpretation: str | None = None
    flag: str | None = None
    collected_at: str | None = None


class ImagingResultData(BaseModel):
    type: str
    finding: str
    impression: str | None = None
    performed_at: str | None = None


class PatientResponse(BaseModel):
    id: str
    mrn: str | None = None
    first_name: str
    last_name: str
    date_of_birth: date
    gender: str | None = None
    age: int | None = None
    insurance_provider: str | None = None
    insurance_plan_name: str | None = None
    insurance_member_id: str | None = None
    code_status: str = "FULL_CODE"
    allergies: list | None = []
    primary_language: str = "English"
    vitals: dict | None = {}
    active_conditions: list | None = []
    current_medications: list | None = []
    lab_results: list | None = []
    imaging_results: list | None = []
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class PatientListResponse(BaseModel):
    data: list[PatientResponse]
    total_count: int
