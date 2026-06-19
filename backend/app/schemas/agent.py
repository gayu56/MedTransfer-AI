from pydantic import BaseModel


class AgentChatRequest(BaseModel):
    session_id: str | None = None
    message: str
    transfer_id: str | None = None
    patient_id: str | None = None


class AgentAction(BaseModel):
    action: str
    details: str


class SuggestedAction(BaseModel):
    action: str
    label: str
    data: dict | None = None


class ToolCallRecord(BaseModel):
    tool: str
    arguments: dict = {}
    result_preview: str = ""


class AgentChatResponse(BaseModel):
    session_id: str
    response: str
    actions_taken: list[AgentAction] = []
    suggested_actions: list[SuggestedAction] = []
    tool_calls: list[ToolCallRecord] = []


class SBARGenerateRequest(BaseModel):
    patient_id: str
    reason_for_transfer: str
    urgency: str
    requested_specialty: str | None = None
    additional_context: str | None = None


class SBARVerificationFlag(BaseModel):
    section: str
    value: str
    type: str
    message: str


class SBARVerification(BaseModel):
    verified: bool = True
    verification_score: float = 100.0
    total_values_checked: int = 0
    verified_count: int = 0
    flags: list[SBARVerificationFlag] = []
    source_data_available: bool = True


class SBARResponse(BaseModel):
    id: str | None = None
    situation: str
    background: str
    assessment: str
    recommendation: str
    generated_by_ai: bool = True
    human_verified: bool = False
    edited_by_human: bool = False
    verification: SBARVerification | None = None


class SBARReviewRequest(BaseModel):
    situation: str | None = None
    background: str | None = None
    assessment: str | None = None
    recommendation: str | None = None
    approved: bool = True
