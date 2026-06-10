from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.facility import Facility
from app.schemas.call_log import (
    CallLogCreate, CallLogUpdate, CallLogResponse,
    CallScriptRequest, CallScriptResponse, ConfirmAcceptanceRequest,
)
from app.services import call_service

router = APIRouter()

DEFAULT_USER_ID = "user-sarah-01"


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
            created_at=c.created_at,
        )
        for c in calls
    ]


@router.post("/auto-call/{transfer_id}")
async def run_auto_call(transfer_id: str, db: AsyncSession = Depends(get_db)):
    """Run AI-simulated call sequence. Does NOT auto-accept — requires human confirmation."""
    results = await call_service.run_auto_call_sequence(db, transfer_id)
    pending = any(r["outcome"] == "PENDING_CONFIRMATION" for r in results)
    return {
        "transfer_id": transfer_id,
        "calls_made": len(results),
        "results": results,
        "needs_confirmation": pending,
        "pending_facility": next((r["facility_name"] for r in results if r["outcome"] == "PENDING_CONFIRMATION"), None),
        "pending_call_id": next((r["call_id"] for r in results if r["outcome"] == "PENDING_CONFIRMATION"), None),
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
