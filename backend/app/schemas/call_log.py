from datetime import datetime
from pydantic import BaseModel


class CallLogCreate(BaseModel):
    transfer_id: str
    facility_id: str
    contact_name: str | None = None
    contact_role: str | None = None
    phone_number: str | None = None
    notes: str | None = None


class CallLogUpdate(BaseModel):
    outcome: str  # CONNECTED, ACCEPTED, DECLINED, NO_ANSWER, VOICEMAIL, CALLBACK_REQUESTED, TRANSFERRED_TO_MD
    duration_seconds: int | None = None
    notes: str | None = None
    decline_reason: str | None = None
    callback_time: str | None = None
    contact_name: str | None = None
    contact_role: str | None = None
    accepting_physician: str | None = None  # REQUIRED when outcome is ACCEPTED


class TranscriptTurn(BaseModel):
    speaker: str
    text: str


class CallLogResponse(BaseModel):
    id: str
    transfer_id: str
    facility_id: str
    facility_name: str | None = None
    contact_name: str | None = None
    contact_role: str | None = None
    phone_number: str | None = None
    outcome: str = "PENDING"
    duration_seconds: int | None = None
    decline_reason: str | None = None
    callback_time: str | None = None
    notes: str | None = None
    call_script_used: bool = False
    is_simulated: bool = False
    human_confirmed: bool = False
    accepting_physician: str | None = None
    bed_type: str | None = None
    transcript: list[TranscriptTurn] = []
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class ConfirmAcceptanceRequest(BaseModel):
    call_id: str
    accepting_physician: str  # Name of the real clinician who accepted
    contact_name: str | None = None
    contact_role: str | None = None
    notes: str | None = None


class CallScriptRequest(BaseModel):
    transfer_id: str
    facility_id: str


class CallScriptResponse(BaseModel):
    facility_name: str
    facility_phone: str | None = None
    contact_info: str | None = None
    script: str
    key_points: list[str] = []
    questions_to_ask: list[str] = []
