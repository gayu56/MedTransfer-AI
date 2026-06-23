from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.clinical_summary import ClinicalSummary
from app.schemas.transfer import (
    TransferCreate, TransferAccept, TransferDecline, TransferStatusUpdate,
    TransferResponse, TransferListResponse, FacilityMatchResponse,
    FacilitySummary, ClinicalSummaryResponse, ComplianceResponse,
    TimelineEvent, TransportResponse,
)
from app.schemas.patient import PatientResponse
from app.services import transfer_service, facility_service

router = APIRouter()

# Default IDs for MVP (no auth yet)
DEFAULT_USER_ID = "user-np-sarah"
DEFAULT_FACILITY_ID = "facility-urgent-care-east"


def _build_transfer_response(transfer) -> TransferResponse:
    patient_resp = None
    if transfer.patient:
        p = transfer.patient
        patient_resp = PatientResponse(
            id=p.id, mrn=p.mrn, first_name=p.first_name, last_name=p.last_name,
            date_of_birth=p.date_of_birth, gender=p.gender, age=p.age,
            insurance_provider=p.insurance_provider, insurance_plan_name=p.insurance_plan_name,
            code_status=p.code_status, allergies=p.allergies or [],
            vitals=p.vitals or {}, active_conditions=p.active_conditions or [],
            current_medications=p.current_medications or [], lab_results=p.lab_results or [],
            imaging_results=p.imaging_results or [], created_at=p.created_at,
        )

    sending = None
    if transfer.sending_facility:
        f = transfer.sending_facility
        sending = FacilitySummary(id=f.id, name=f.name, phone=f.phone, city=f.city, state=f.state)

    receiving = None
    if transfer.receiving_facility:
        f = transfer.receiving_facility
        receiving = FacilitySummary(id=f.id, name=f.name, phone=f.phone, city=f.city, state=f.state)

    clinical = None
    if transfer.clinical_summary:
        cs = transfer.clinical_summary
        clinical = ClinicalSummaryResponse(
            id=cs.id, situation=cs.situation, background=cs.background,
            assessment=cs.assessment, recommendation=cs.recommendation,
            generated_by_ai=cs.generated_by_ai, version=cs.version,
            human_verified=cs.human_verified, edited_by_human=cs.edited_by_human,
            reviewed_at=cs.reviewed_at, created_at=cs.created_at,
        )

    compliance = None
    if transfer.compliance_record:
        cr = transfer.compliance_record
        compliance = ComplianceResponse(
            id=cr.id, mse_completed=cr.mse_completed,
            stabilization_attempted=cr.stabilization_attempted,
            md_certification_signed=cr.md_certification_signed,
            consent_obtained=cr.consent_obtained,
            receiving_facility_confirmed=cr.receiving_facility_confirmed,
            transport_appropriate=cr.transport_appropriate,
            records_sent=cr.records_sent,
            all_checks_passed=cr.all_checks_passed,
        )

    matches = []
    for m in (transfer.facility_matches or []):
        fm = FacilityMatchResponse(
            rank=m.rank, facility_id=m.facility_id,
            facility_name=m.facility.name if m.facility else None,
            facility_city=m.facility.city if m.facility else None,
            facility_state=m.facility.state if m.facility else None,
            overall_score=m.overall_score, specialty_score=m.specialty_score,
            bed_availability_score=m.bed_availability_score, distance_score=m.distance_score,
            insurance_score=m.insurance_score, distance_miles=m.distance_miles,
            estimated_transport_min=m.estimated_transport_min, status=m.status,
        )
        matches.append(fm)

    timeline = [
        TimelineEvent(
            id=t.id, event_type=t.event_type, event_description=t.event_description,
            triggered_by_system=t.triggered_by_system, created_at=t.created_at,
        ) for t in (transfer.timeline or [])
    ]

    transport = None
    if transfer.transport_request:
        tr = transfer.transport_request
        transport = TransportResponse(
            id=tr.id, transport_level=tr.transport_level,
            transport_provider_name=tr.transport_provider_name,
            status=tr.status, estimated_pickup_at=tr.estimated_pickup_at,
        )

    return TransferResponse(
        id=transfer.id, transfer_number=transfer.transfer_number,
        status=transfer.status, urgency=transfer.urgency,
        reason_for_transfer=transfer.reason_for_transfer,
        requested_specialty=transfer.requested_specialty,
        requested_unit_type=transfer.requested_unit_type,
        additional_notes=transfer.additional_notes,
        patient=patient_resp, sending_facility=sending,
        receiving_facility=receiving, clinical_summary=clinical,
        compliance_record=compliance, transport_request=transport,
        facility_matches=matches, timeline=timeline,
        initiated_at=transfer.initiated_at, accepted_at=transfer.accepted_at,
        completed_at=transfer.completed_at, created_at=transfer.created_at,
        updated_at=transfer.updated_at,
    )


@router.post("", response_model=TransferResponse, status_code=201)
async def create_transfer(req: TransferCreate, db: AsyncSession = Depends(get_db)):
    transfer = await transfer_service.create_transfer(
        db=db,
        patient_id=req.patient_id,
        sending_facility_id=DEFAULT_FACILITY_ID,
        initiated_by_user_id=DEFAULT_USER_ID,
        urgency=req.urgency,
        reason_for_transfer=req.reason_for_transfer,
        requested_specialty=req.requested_specialty,
        requested_unit_type=req.requested_unit_type,
        additional_notes=req.additional_notes,
    )
    # AGENTIC MESH: FacilityAgent matches and ranks hospitals
    from app.ai.agents.orchestrator_agent import orchestrator_agent
    await orchestrator_agent.fallback(
        task=f"Match facilities for transfer {transfer.id}",
        db=db,
        context={
            "target_agent": "facility",
            "action": "match",
            "transfer_id": transfer.id,
            "sending_facility_id": DEFAULT_FACILITY_ID,
            "required_specialty": req.requested_specialty,
            "required_unit_type": req.requested_unit_type,
        },
    )
    transfer.status = "PENDING_REVIEW"

    # Link previously generated SBAR to this transfer
    if req.clinical_summary_id:
        result = await db.execute(
            select(ClinicalSummary).where(ClinicalSummary.id == req.clinical_summary_id)
        )
        summary = result.scalar_one_or_none()
        if summary:
            summary.transfer_id = transfer.id

    await db.flush()

    full_transfer = await transfer_service.get_transfer(db, transfer.id)
    return _build_transfer_response(full_transfer)


@router.get("", response_model=TransferListResponse)
async def list_transfers(
    status: str | None = None,
    urgency: str | None = None,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    transfers, total = await transfer_service.list_transfers(
        db, status=status, urgency=urgency, limit=limit, offset=offset,
    )
    return TransferListResponse(
        data=[_build_transfer_response(t) for t in transfers],
        total_count=total,
    )


@router.get("/{transfer_id}", response_model=TransferResponse)
async def get_transfer(transfer_id: str, db: AsyncSession = Depends(get_db)):
    transfer = await transfer_service.get_transfer(db, transfer_id)
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")
    return _build_transfer_response(transfer)


@router.post("/{transfer_id}/accept", response_model=TransferResponse)
async def accept_transfer(
    transfer_id: str,
    req: TransferAccept,
    db: AsyncSession = Depends(get_db),
):
    transfer = await transfer_service.get_transfer(db, transfer_id)
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")

    # Find the first SENT facility match
    sent_match = next((m for m in transfer.facility_matches if m.status == "SENT"), None)
    facility_id = sent_match.facility_id if sent_match else transfer.sending_facility_id

    updated = await transfer_service.accept_transfer(
        db, transfer_id, DEFAULT_USER_ID, facility_id, req.accepting_physician_notes,
    )
    full = await transfer_service.get_transfer(db, transfer_id)
    return _build_transfer_response(full)


@router.post("/{transfer_id}/decline", response_model=TransferResponse)
async def decline_transfer(
    transfer_id: str,
    req: TransferDecline,
    db: AsyncSession = Depends(get_db),
):
    transfer = await transfer_service.get_transfer(db, transfer_id)
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")

    sent_match = next((m for m in transfer.facility_matches if m.status == "SENT"), None)
    facility_id = sent_match.facility_id if sent_match else ""

    updated = await transfer_service.decline_transfer(
        db, transfer_id, facility_id, req.reason, req.notes,
    )
    full = await transfer_service.get_transfer(db, transfer_id)
    return _build_transfer_response(full)


@router.patch("/{transfer_id}/status", response_model=TransferResponse)
async def update_status(
    transfer_id: str,
    req: TransferStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    # FIX 3 + AGENTIC MESH: ComplianceAgent enforces EMTALA dispatch gate
    if req.status == "TRANSPORT_READY":
        from app.ai.agents.orchestrator_agent import orchestrator_agent
        gate_result = await orchestrator_agent.fallback(
            task=f"Enforce dispatch gate for transfer {transfer_id}",
            db=db,
            context={
                "target_agent": "compliance",
                "action": "enforce_gate",
                "transfer_id": transfer_id,
            },
        )
        compliance_result = gate_result.get("result", {})
        if not compliance_result.get("allowed", False):
            raise HTTPException(
                status_code=400,
                detail=compliance_result.get("message", "EMTALA HARD STOP: Compliance checks incomplete"),
            )

    updated = await transfer_service.update_transfer_status(
        db, transfer_id, req.status, req.notes, DEFAULT_USER_ID,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Transfer not found")
    full = await transfer_service.get_transfer(db, transfer_id)
    return _build_transfer_response(full)
