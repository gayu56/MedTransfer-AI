from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.facility import Facility
from app.schemas.call_log import (
    CallLogCreate, CallLogUpdate, CallLogResponse,
    CallScriptRequest, CallScriptResponse, ConfirmAcceptanceRequest,
)
from app.services import call_service

router = APIRouter()

DEFAULT_USER_ID = "user-np-sarah"


@router.post("", response_model=CallLogResponse, status_code=201)
async def create_call(req: CallLogCreate, db: AsyncSession = Depends(get_db)):
    call = await call_service.create_call_log(
        db=db,
        transfer_id=req.transfer_id,
        facility_id=req.facility_id,
        called_by_user_id=DEFAULT_USER_ID,
        contact_name=req.contact_name,
        contact_role=req.contact_role,
        phone_number=req.phone_number,
        notes=req.notes,
    )
    facility = await db.get(Facility, call.facility_id)
    return CallLogResponse(
        id=call.id,
        transfer_id=call.transfer_id,
        facility_id=call.facility_id,
        facility_name=facility.name if facility else None,
        contact_name=call.contact_name,
        contact_role=call.contact_role,
        phone_number=call.phone_number,
        outcome=call.outcome,
        duration_seconds=call.duration_seconds,
        notes=call.notes,
        call_script_used=call.call_script_used,
        created_at=call.created_at,
    )


@router.patch("/{call_id}", response_model=CallLogResponse)
async def update_call(call_id: str, req: CallLogUpdate, db: AsyncSession = Depends(get_db)):
    call = await call_service.update_call_log(
        db=db,
        call_id=call_id,
        outcome=req.outcome,
        duration_seconds=req.duration_seconds,
        notes=req.notes,
        decline_reason=req.decline_reason,
        callback_time=req.callback_time,
        contact_name=req.contact_name,
        contact_role=req.contact_role,
    )
    if not call:
        raise HTTPException(status_code=404, detail="Call log not found")

    facility = await db.get(Facility, call.facility_id)
    return CallLogResponse(
        id=call.id,
        transfer_id=call.transfer_id,
        facility_id=call.facility_id,
        facility_name=facility.name if facility else None,
        contact_name=call.contact_name,
        contact_role=call.contact_role,
        phone_number=call.phone_number,
        outcome=call.outcome,
        duration_seconds=call.duration_seconds,
        decline_reason=call.decline_reason,
        callback_time=call.callback_time,
        notes=call.notes,
        call_script_used=call.call_script_used,
        created_at=call.created_at,
    )


def _parse_transcript(raw: str | None) -> list:
    if not raw:
        return []
    import json
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except (ValueError, TypeError):
        return []


@router.get("/transfer/{transfer_id}", response_model=list[CallLogResponse])
async def get_transfer_calls(transfer_id: str, db: AsyncSession = Depends(get_db)):
    calls = await call_service.get_calls_for_transfer(db, transfer_id)
    return [
        CallLogResponse(
            id=c.id,
            transfer_id=c.transfer_id,
            facility_id=c.facility_id,
            facility_name=c.facility.name if c.facility else None,
            contact_name=c.contact_name,
            contact_role=c.contact_role,
            phone_number=c.phone_number,
            outcome=c.outcome,
            duration_seconds=c.duration_seconds,
            decline_reason=c.decline_reason,
            callback_time=c.callback_time,
            notes=c.notes,
            call_script_used=c.call_script_used,
            is_simulated=c.is_simulated,
            human_confirmed=c.human_confirmed,
            accepting_physician=c.accepting_physician,
            bed_type=c.bed_type,
            transcript=_parse_transcript(c.transcript),
            created_at=c.created_at,
        )
        for c in calls
    ]


@router.post("/auto-call/{transfer_id}")
async def run_auto_call(transfer_id: str, db: AsyncSession = Depends(get_db)):
    """AGENTIC MESH: Orchestrator delegates broadcast to OutreachAgent.
    OutreachAgent contacts all facilities, FacilityAgent updates beds on accept,
    ComplianceAgent starts monitoring EMTALA after acceptance."""
    from app.models.clinical_summary import ClinicalSummary
    from app.ai.agents.orchestrator_agent import orchestrator_agent

    # Gate: SBAR must be human-verified before broadcast
    sbar_result = await db.execute(
        select(ClinicalSummary).where(ClinicalSummary.transfer_id == transfer_id)
    )
    sbar = sbar_result.scalar_one_or_none()
    if not sbar or not sbar.human_verified:
        raise HTTPException(
            status_code=400,
            detail="SBAR must be reviewed and approved by a clinician before broadcasting.",
        )

    result = await orchestrator_agent.fallback(
        task=f"Broadcast transfer {transfer_id} to all matched facilities",
        db=db,
        context={
            "target_agent": "outreach",
            "action": "broadcast",
            "transfer_id": transfer_id,
        },
    )

    # Extract the outreach result for backward-compatible response
    outreach_result = result.get("result", {})
    results = outreach_result.get("results", [])
    accepted = next((r for r in results if r.get("accepted")), None)
    return {
        "transfer_id": transfer_id,
        "broadcast_count": outreach_result.get("broadcast_count", len(results)),
        "results": results,
        "accepted": accepted is not None,
        "accepted_facility": accepted["facility_name"] if accepted else None,
        "accepted_by": accepted["contact_name"] if accepted else None,
        "agent_mesh": True,
        "orchestrator_response": result.get("response"),
    }


@router.post("/ai-call/{transfer_id}")
async def run_ai_call(transfer_id: str, db: AsyncSession = Depends(get_db)):
    """PHASE 1 AUDIO AGENT: The AI calls every matched facility, holds a back-and-forth
    conversation, and records transcripts + outcomes. Acceptances are recorded as
    PROPOSED_ACCEPT only — a clinician must confirm (with accepting physician) before
    the transfer is locked. The AI never finalizes the decision."""
    from app.models.clinical_summary import ClinicalSummary

    # Gate: SBAR must be human-verified before any outreach
    sbar_result = await db.execute(
        select(ClinicalSummary).where(ClinicalSummary.transfer_id == transfer_id)
    )
    sbar = sbar_result.scalar_one_or_none()
    if not sbar or not sbar.human_verified:
        raise HTTPException(
            status_code=400,
            detail="SBAR must be reviewed and approved by a clinician before the AI can call facilities.",
        )

    results = await call_service.run_ai_call_parallel(db, transfer_id)
    proposed = [r for r in results if r.get("proposed")]
    superseded = [r for r in results if r.get("superseded")]
    return {
        "transfer_id": transfer_id,
        "call_count": len(results),
        "results": results,
        "has_proposed_acceptance": len(proposed) > 0,
        "proposed_count": len(proposed),
        "superseded_count": len(superseded),
        "parallel": True,
    }


@router.post("/ai-call-retry/{transfer_id}")
async def run_ai_call_with_retry(transfer_id: str, db: AsyncSession = Depends(get_db)):
    """AI calls with auto-retry. If all facilities decline, automatically expands
    the search radius and calls newly found facilities. Up to 3 rounds total."""
    from app.models.clinical_summary import ClinicalSummary

    sbar_result = await db.execute(
        select(ClinicalSummary).where(ClinicalSummary.transfer_id == transfer_id)
    )
    sbar = sbar_result.scalar_one_or_none()
    if not sbar or not sbar.human_verified:
        raise HTTPException(
            status_code=400,
            detail="SBAR must be reviewed and approved by a clinician before the AI can call facilities.",
        )

    result = await call_service.run_ai_call_with_retry(db, transfer_id)
    return {
        "transfer_id": transfer_id,
        **result,
    }


@router.post("/confirm-acceptance")
async def confirm_acceptance(req: ConfirmAcceptanceRequest, db: AsyncSession = Depends(get_db)):
    """Human-confirmed acceptance. Requires accepting physician name. This is the ONLY path to ACCEPTED status."""
    if not req.accepting_physician or not req.accepting_physician.strip():
        raise HTTPException(status_code=400, detail="Accepting physician name is required for EMTALA compliance")

    call = await call_service.confirm_acceptance(
        db=db,
        call_id=req.call_id,
        accepting_physician=req.accepting_physician.strip(),
        contact_name=req.contact_name,
        contact_role=req.contact_role,
        notes=req.notes,
    )
    if not call:
        raise HTTPException(status_code=404, detail="Call log not found")

    facility = await db.get(Facility, call.facility_id)
    return {
        "status": "confirmed",
        "transfer_status": "ACCEPTED",
        "facility_name": facility.name if facility else "Unknown",
        "accepting_physician": call.accepting_physician,
        "message": f"Transfer accepted by {facility.name if facility else 'facility'} — confirmed by Dr. {call.accepting_physician}",
    }


@router.get("/mesh-status/{transfer_id}")
async def get_mesh_status(transfer_id: str):
    """Get the agentic mesh event log for a transfer — shows inter-agent communication."""
    from app.ai.agents.orchestrator_agent import orchestrator_agent
    return orchestrator_agent._get_mesh_status(transfer_id)


@router.get("/mesh-status")
async def get_full_mesh_status():
    """Get the full agentic mesh event log — all agents, all transfers."""
    from app.ai.agents.orchestrator_agent import orchestrator_agent
    return orchestrator_agent._get_mesh_status()


@router.post("/script", response_model=CallScriptResponse)
async def get_call_script(req: CallScriptRequest, db: AsyncSession = Depends(get_db)):
    result = await call_service.generate_call_script(
        db=db,
        transfer_id=req.transfer_id,
        facility_id=req.facility_id,
    )
    return CallScriptResponse(
        facility_name=result.get("facility_name", "Unknown"),
        facility_phone=result.get("facility_phone"),
        script=result.get("script", ""),
        key_points=result.get("key_points", []),
        questions_to_ask=result.get("questions_to_ask", []),
    )
