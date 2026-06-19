import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.patient import Patient
from app.models.clinical_summary import ClinicalSummary
from app.schemas.agent import (
    AgentChatRequest, AgentChatResponse, AgentAction, SuggestedAction,
    SBARGenerateRequest, SBARResponse, SBARVerification, SBARVerificationFlag,
    SBARReviewRequest,
)
from app.ai.sbar_generator import generate_sbar
from app.ai.sbar_verifier import verify_sbar_against_ehr
from app.ai.orchestrator import run_agent

router = APIRouter()

# In-memory session store for conversation history (MVP — use Redis in production)
_sessions: dict[str, list[dict]] = {}


@router.post("/chat", response_model=AgentChatResponse)
async def chat_with_agent(req: AgentChatRequest, db: AsyncSession = Depends(get_db)):
    session_id = req.session_id or str(uuid.uuid4())

    # Get or create conversation history for this session
    history = _sessions.get(session_id, [])

    # Run the orchestrator agent
    result = await run_agent(
        message=req.message,
        db=db,
        session_id=session_id,
        transfer_id=req.transfer_id,
        patient_id=req.patient_id,
        conversation_history=history,
    )

    # Save conversation history
    history.append({"role": "user", "content": req.message})
    history.append({"role": "assistant", "content": result["response"]})
    _sessions[session_id] = history[-20:]  # Keep last 20 messages

    return AgentChatResponse(
        session_id=session_id,
        response=result["response"],
        actions_taken=[
            AgentAction(action=a["action"], details=a["details"])
            for a in result.get("actions_taken", [])
        ],
        suggested_actions=[
            SuggestedAction(action=a["action"], label=a["label"], data=a.get("data"))
            for a in result.get("suggested_actions", [])
        ],
        tool_calls=result.get("tool_calls_made", []),
    )


@router.post("/sbar/generate", response_model=SBARResponse)
async def generate_sbar_endpoint(req: SBARGenerateRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Patient).where(Patient.id == req.patient_id))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    sbar_dict, was_ai = await generate_sbar(
        patient=patient,
        reason=req.reason_for_transfer,
        urgency=req.urgency,
        specialty=req.requested_specialty,
        additional_context=req.additional_context,
    )

    # Save to DB if transfer_id provided
    summary = ClinicalSummary(
        transfer_id=None,  # Will be linked when transfer is created
        patient_id=patient.id,
        situation=sbar_dict["situation"],
        background=sbar_dict["background"],
        assessment=sbar_dict["assessment"],
        recommendation=sbar_dict["recommendation"],
        vitals=patient.vitals,
        active_conditions=patient.active_conditions,
        current_medications=patient.current_medications,
        lab_results=patient.lab_results,
        imaging_results=patient.imaging_results,
        generated_by_ai=was_ai,
        ai_model_version="gpt-4" if was_ai else "template-v1",
    )
    db.add(summary)
    await db.flush()

    # Run hallucination guard — verify AI output against source EHR
    verification_data = None
    if was_ai:
        vr = verify_sbar_against_ehr(
            sbar=sbar_dict,
            patient=patient,
            reason=req.reason_for_transfer,
            urgency=req.urgency,
        )
        verification_data = SBARVerification(
            verified=vr["verified"],
            verification_score=vr["verification_score"],
            total_values_checked=vr["total_values_checked"],
            verified_count=vr["verified_count"],
            flags=[SBARVerificationFlag(**f) for f in vr["flags"]],
            source_data_available=vr["source_data_available"],
        )

    return SBARResponse(
        id=summary.id,
        situation=sbar_dict["situation"],
        background=sbar_dict["background"],
        assessment=sbar_dict["assessment"],
        recommendation=sbar_dict["recommendation"],
        generated_by_ai=was_ai,
        human_verified=False,
        edited_by_human=False,
        verification=verification_data,
    )


@router.patch("/sbar/{sbar_id}/review")
async def review_sbar(sbar_id: str, req: SBARReviewRequest, db: AsyncSession = Depends(get_db)):
    """Human-in-the-loop: review, optionally edit, and approve an AI-generated SBAR."""
    from datetime import datetime, timezone

    result = await db.execute(select(ClinicalSummary).where(ClinicalSummary.id == sbar_id))
    summary = result.scalar_one_or_none()
    if not summary:
        raise HTTPException(status_code=404, detail="SBAR not found")

    edited = False
    if req.situation is not None and req.situation != summary.situation:
        summary.situation = req.situation
        edited = True
    if req.background is not None and req.background != summary.background:
        summary.background = req.background
        edited = True
    if req.assessment is not None and req.assessment != summary.assessment:
        summary.assessment = req.assessment
        edited = True
    if req.recommendation is not None and req.recommendation != summary.recommendation:
        summary.recommendation = req.recommendation
        edited = True

    if edited:
        summary.edited_by_human = True
        summary.version += 1

    if req.approved:
        summary.human_verified = True
        summary.reviewed_at = datetime.now(timezone.utc)
        summary.reviewed_by_user_id = "user-sarah-01"  # TODO: from auth context

    summary.updated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.commit()

    return {
        "id": summary.id,
        "human_verified": summary.human_verified,
        "edited_by_human": summary.edited_by_human,
        "version": summary.version,
        "reviewed_at": summary.reviewed_at.isoformat() if summary.reviewed_at else None,
    }
